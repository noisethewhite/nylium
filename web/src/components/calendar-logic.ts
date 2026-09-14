import type { ObjectView, PropValue, TypeView } from "../contracts";
import { PropValues, TypeNames } from "../contracts";
import { MONTH_NAMES } from "../month-names";
import { ObjectLabels } from "./object-labels";

/** ADR-0009 (section 2): the calendar grid's domain logic, pulled out of
 * CalendarView so the component is a thin renderer. A generic month grid
 * that places any object with a Date/Datetime prop. The MVP convention is
 * Event.start (span to end) and Task.due, but the generic fallback reads
 * any date-typed prop, so a future "show Note.reminder_on here too" is
 * configuration, not code. */

/** "YYYY-MM-DD" — zero-padded and fixed-length, so string comparison is
 * chronological. */
export type DayKey = string;

export interface DateSpan {
  start: DayKey;
  end: DayKey; // inclusive
  time: string | null; // "HH:MM" when the anchor is a Datetime stamp
}

export interface CalendarEntry {
  object: ObjectView;
  typeName: string;
  span: DateSpan;
}

export interface CalendarCell {
  key: string;
  dayKey: DayKey | null;
  day: number | null;
}

/** Static helpers for the month grid — namespace-only, never instantiated. */
export abstract class CalendarGrid {
  static readonly COLUMNS_PER_WEEK = 7;
  static readonly WEEKDAY_LABELS: readonly string[] = [
    "Sun",
    "Mon",
    "Tue",
    "Wed",
    "Thu",
    "Fri",
    "Sat",
  ];
  private static readonly MILLIS_PER_DAY = 86_400_000;

  /** MVP convention: which prop(s) a type's objects are dated by. `start`
   * is required, `end` is the optional span. Types absent from the map fall
   * back to "any Date/Datetime prop". Domain types are user data, not engine
   * builtins — these names are ordinary strings, not TypeNames members. */
  private static readonly CALENDAR_CONVENTION: Readonly<
    Record<string, { start: string; end?: string }>
  > = {
    Event: { start: "start", end: "end" },
    Task: { start: "due" },
  };

  /** Date/Datetime wire values are ISO text ("YYYY-MM-DD" / "YYYY-MM-DDTHH:MM…");
   * the day key is the leading date segment. */
  private static readonly DAY_KEY_PATTERN = /^\d{4}-\d{2}-\d{2}/;
  private static readonly TIME_PATTERN = /^\d{4}-\d{2}-\d{2}T(\d{2}:\d{2})/;

  private static pad2(n: number): string {
    return String(n).padStart(2, "0");
  }

  static dayKeyFromParts(year: number, month: number, day: number): DayKey {
    return `${year}-${CalendarGrid.pad2(month + 1)}-${CalendarGrid.pad2(day)}`;
  }

  private static dayKeyOf(value: string): DayKey | null {
    const match = CalendarGrid.DAY_KEY_PATTERN.exec(value);
    return match === null ? null : match[0];
  }

  /** "YYYY-MM-DDTHH:MM…" -> "HH:MM"; null for date-only stamps. */
  private static timeOf(value: string): string | null {
    const match = CalendarGrid.TIME_PATTERN.exec(value);
    return match?.[1] ?? null;
  }

  private static scalarDateString(value: PropValue | undefined): string | null {
    if (value === undefined || !PropValues.isScalar(value)) {
      return null;
    }
    return typeof value.value === "string" ? value.value : null;
  }

  /** The date spans an object occupies — convention first, then any
   * date-typed prop. Returns [] when the object has no dated anchor. */
  private static spansOf(object: ObjectView, type: TypeView | undefined): DateSpan[] {
    if (type === undefined) {
      return [];
    }
    const convention = CalendarGrid.CALENDAR_CONVENTION[type.name];
    if (convention !== undefined) {
      const startRaw = CalendarGrid.scalarDateString(object.props[convention.start]);
      if (startRaw === null) {
        return [];
      }
      const start = CalendarGrid.dayKeyOf(startRaw);
      if (start === null) {
        return [];
      }
      const endKey = convention.end;
      const endRaw = endKey === undefined ? null : CalendarGrid.scalarDateString(object.props[endKey]);
      const endDay = endRaw === null ? null : CalendarGrid.dayKeyOf(endRaw);
      const end = endDay === null || endDay < start ? start : endDay;
      return [{ start, end, time: CalendarGrid.timeOf(startRaw) }];
    }
    const spans: DateSpan[] = [];
    for (const prop of type.props) {
      if (!TypeNames.isDateType(prop.value_type)) {
        continue;
      }
      const raw = CalendarGrid.scalarDateString(object.props[prop.key]);
      if (raw === null) {
        continue;
      }
      const day = CalendarGrid.dayKeyOf(raw);
      if (day === null) {
        continue;
      }
      spans.push({ start: day, end: day, time: CalendarGrid.timeOf(raw) });
    }
    return spans;
  }

  /** Inclusive day keys in [start, end], walked in UTC so timezone/DST can
   * never skew the enumeration. */
  private static *daysBetween(start: DayKey, end: DayKey): Generator<DayKey> {
    const cursor = new Date(`${start}T00:00:00Z`);
    const last = new Date(`${end}T00:00:00Z`);
    for (let t = cursor.getTime(); t <= last.getTime(); t += CalendarGrid.MILLIS_PER_DAY) {
      const stamp = new Date(t);
      yield CalendarGrid.dayKeyFromParts(
        stamp.getUTCFullYear(),
        stamp.getUTCMonth(),
        stamp.getUTCDate(),
      );
    }
  }

  static entriesByDay(
    objects: readonly ObjectView[],
    types: readonly TypeView[],
  ): Map<DayKey, CalendarEntry[]> {
    const byDay = new Map<DayKey, CalendarEntry[]>();
    for (const object of objects) {
      const type = types.find((candidate) => candidate.name === object.type_name);
      for (const span of CalendarGrid.spansOf(object, type)) {
        for (const day of CalendarGrid.daysBetween(span.start, span.end)) {
          const existing = byDay.get(day);
          const entry: CalendarEntry = { object, typeName: object.type_name, span };
          if (existing === undefined) {
            byDay.set(day, [entry]);
          } else {
            existing.push(entry);
          }
        }
      }
    }
    return byDay;
  }

  static buildCells(year: number, month: number): CalendarCell[] {
    const leading = new Date(year, month, 1).getDay();
    const count = new Date(year, month + 1, 0).getDate();
    const cells: CalendarCell[] = [];
    for (let i = 0; i < leading; i++) {
      cells.push({ key: `blank-${i}`, dayKey: null, day: null });
    }
    for (let day = 1; day <= count; day++) {
      cells.push({
        key: `${year}-${month}-${day}`,
        dayKey: CalendarGrid.dayKeyFromParts(year, month, day),
        day,
      });
    }
    const trailing =
      (CalendarGrid.COLUMNS_PER_WEEK - (cells.length % CalendarGrid.COLUMNS_PER_WEEK)) %
      CalendarGrid.COLUMNS_PER_WEEK;
    for (let i = 0; i < trailing; i++) {
      cells.push({ key: `trailing-${i}`, dayKey: null, day: null });
    }
    return cells;
  }

  static friendlyDay(key: DayKey): string {
    const [yearPart, monthPart, dayPart] = key.split("-");
    const year = Number.parseInt(yearPart ?? "", 10);
    const month = Number.parseInt(monthPart ?? "", 10) - 1;
    const day = Number.parseInt(dayPart ?? "", 10);
    const weekday = CalendarGrid.WEEKDAY_LABELS[new Date(year, month, day).getDay()];
    return `${weekday}, ${MONTH_NAMES[month]} ${day}, ${year}`;
  }

  static spanLabel(span: DateSpan): string {
    if (span.start !== span.end) {
      return `${span.start} → ${span.end}`;
    }
    return span.time ?? "";
  }

  static sortEntries(entries: CalendarEntry[]): CalendarEntry[] {
    return [...entries].sort((a, b) => {
      const timeA = a.span.time ?? "";
      const timeB = b.span.time ?? "";
      if (timeA !== timeB) {
        return timeA.localeCompare(timeB);
      }
      return ObjectLabels.of(a.object).localeCompare(ObjectLabels.of(b.object));
    });
  }
}
