import type { ReactElement } from "react";
import { useMemo, useState } from "react";
import type { ObjectView, PropValue, TypeView } from "../contracts";
import { PropValues, TypeNames } from "../contracts";
import { useObservable } from "../state/use-observable";
import type { WorkspaceStore } from "../state/workspace";
import { ObjectLabels } from "./object-labels";
import { TypeIcon } from "./type-icon";

/** ADR-0009 (section 2): a generic month grid that places any object with
 * a Date/Datetime prop. The MVP convention is Event.start (span to end)
 * and Task.due, but the generic fallback reads any date-typed prop, so a
 * future "show Note.reminder_on here too" is configuration, not code. */

const COLUMNS_PER_WEEK = 7;
const WEEKDAY_LABELS: readonly string[] = [
  "Sun",
  "Mon",
  "Tue",
  "Wed",
  "Thu",
  "Fri",
  "Sat",
];
const MONTH_NAMES: readonly string[] = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];
const MILLIS_PER_DAY = 86_400_000;

/** MVP convention: which prop(s) a type's objects are dated by. `start`
 * is required, `end` is the optional span. Types absent from the map fall
 * back to "any Date/Datetime prop". Domain types are user data, not engine
 * builtins — these names are ordinary strings, not TypeNames members. */
const CALENDAR_CONVENTION: Readonly<Record<string, { start: string; end?: string }>> = {
  Event: { start: "start", end: "end" },
  Task: { start: "due" },
};

/** "YYYY-MM-DD" — zero-padded and fixed-length, so string comparison is
 * chronological. */
type DayKey = string;

interface DateSpan {
  start: DayKey;
  end: DayKey; // inclusive
  time: string | null; // "HH:MM" when the anchor is a Datetime stamp
}

interface CalendarEntry {
  object: ObjectView;
  typeName: string;
  span: DateSpan;
}

interface CalendarCell {
  key: string;
  dayKey: DayKey | null;
  day: number | null;
}

const pad2 = (n: number): string => String(n).padStart(2, "0");

const dayKeyFromParts = (year: number, month: number, day: number): DayKey =>
  `${year}-${pad2(month + 1)}-${pad2(day)}`;

/** Date/Datetime wire values are ISO text ("YYYY-MM-DD" / "YYYY-MM-DDTHH:MM…");
 * the day key is the leading date segment. */
const DAY_KEY_PATTERN = /^\d{4}-\d{2}-\d{2}/;

function dayKeyOf(value: string): DayKey | null {
  const match = DAY_KEY_PATTERN.exec(value);
  return match === null ? null : match[0];
}

/** "YYYY-MM-DDTHH:MM…" -> "HH:MM"; null for date-only stamps. */
function timeOf(value: string): string | null {
  const match = /^\d{4}-\d{2}-\d{2}T(\d{2}:\d{2})/.exec(value);
  return match?.[1] ?? null;
}

function scalarDateString(value: PropValue | undefined): string | null {
  if (value === undefined || !PropValues.isScalar(value)) {
    return null;
  }
  return typeof value.value === "string" ? value.value : null;
}

/** The date spans an object occupies — convention first, then any
 * date-typed prop. Returns [] when the object has no dated anchor. */
function spansOf(object: ObjectView, type: TypeView | undefined): DateSpan[] {
  if (type === undefined) {
    return [];
  }
  const convention = CALENDAR_CONVENTION[type.name];
  if (convention !== undefined) {
    const startRaw = scalarDateString(object.props[convention.start]);
    if (startRaw === null) {
      return [];
    }
    const start = dayKeyOf(startRaw);
    if (start === null) {
      return [];
    }
    const endKey = convention.end;
    const endRaw = endKey === undefined ? null : scalarDateString(object.props[endKey]);
    const endDay = endRaw === null ? null : dayKeyOf(endRaw);
    const end = endDay === null || endDay < start ? start : endDay;
    return [{ start, end, time: timeOf(startRaw) }];
  }
  const spans: DateSpan[] = [];
  for (const prop of type.props) {
    if (!TypeNames.isDateType(prop.value_type)) {
      continue;
    }
    const raw = scalarDateString(object.props[prop.key]);
    if (raw === null) {
      continue;
    }
    const day = dayKeyOf(raw);
    if (day === null) {
      continue;
    }
    spans.push({ start: day, end: day, time: timeOf(raw) });
  }
  return spans;
}

/** Inclusive day keys in [start, end], walked in UTC so timezone/DST can
 * never skew the enumeration. */
function* daysBetween(start: DayKey, end: DayKey): Generator<DayKey> {
  const cursor = new Date(`${start}T00:00:00Z`);
  const last = new Date(`${end}T00:00:00Z`);
  for (let t = cursor.getTime(); t <= last.getTime(); t += MILLIS_PER_DAY) {
    const stamp = new Date(t);
    yield dayKeyFromParts(stamp.getUTCFullYear(), stamp.getUTCMonth(), stamp.getUTCDate());
  }
}

function entriesByDay(
  objects: readonly ObjectView[],
  types: readonly TypeView[],
): Map<DayKey, CalendarEntry[]> {
  const byDay = new Map<DayKey, CalendarEntry[]>();
  for (const object of objects) {
    const type = types.find((candidate) => candidate.name === object.type_name);
    for (const span of spansOf(object, type)) {
      for (const day of daysBetween(span.start, span.end)) {
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

function buildCells(year: number, month: number): CalendarCell[] {
  const leading = new Date(year, month, 1).getDay();
  const count = new Date(year, month + 1, 0).getDate();
  const cells: CalendarCell[] = [];
  for (let i = 0; i < leading; i++) {
    cells.push({ key: `blank-${i}`, dayKey: null, day: null });
  }
  for (let day = 1; day <= count; day++) {
    cells.push({ key: `${year}-${month}-${day}`, dayKey: dayKeyFromParts(year, month, day), day });
  }
  const trailing = (COLUMNS_PER_WEEK - (cells.length % COLUMNS_PER_WEEK)) % COLUMNS_PER_WEEK;
  for (let i = 0; i < trailing; i++) {
    cells.push({ key: `trailing-${i}`, dayKey: null, day: null });
  }
  return cells;
}

function friendlyDay(key: DayKey): string {
  const [yearPart, monthPart, dayPart] = key.split("-");
  const year = Number.parseInt(yearPart ?? "", 10);
  const month = Number.parseInt(monthPart ?? "", 10) - 1;
  const day = Number.parseInt(dayPart ?? "", 10);
  const weekday = WEEKDAY_LABELS[new Date(year, month, day).getDay()];
  return `${weekday}, ${MONTH_NAMES[month]} ${day}, ${year}`;
}

function spanLabel(span: DateSpan): string {
  if (span.start !== span.end) {
    return `${span.start} → ${span.end}`;
  }
  return span.time ?? "";
}

function sortEntries(entries: CalendarEntry[]): CalendarEntry[] {
  return [...entries].sort((a, b) => {
    const timeA = a.span.time ?? "";
    const timeB = b.span.time ?? "";
    if (timeA !== timeB) {
      return timeA.localeCompare(timeB);
    }
    return ObjectLabels.of(a.object).localeCompare(ObjectLabels.of(b.object));
  });
}

export function CalendarView(props: { workspace: WorkspaceStore }): ReactElement {
  const state = useObservable(props.workspace);
  const [cursor, setCursor] = useState<{ year: number; month: number }>(() => {
    const now = new Date();
    return { year: now.getFullYear(), month: now.getMonth() };
  });
  const [selectedDay, setSelectedDay] = useState<DayKey | null>(null);

  const todayKey = useMemo(() => {
    const now = new Date();
    return dayKeyFromParts(now.getFullYear(), now.getMonth(), now.getDate());
  }, []);

  const byDay = useMemo(
    () => entriesByDay(state.objects, state.types),
    [state.objects, state.types],
  );

  const prevMonth = (): void => {
    setCursor((current) =>
      current.month === 0
        ? { year: current.year - 1, month: 11 }
        : { ...current, month: current.month - 1 },
    );
  };

  const nextMonth = (): void => {
    setCursor((current) =>
      current.month === 11
        ? { year: current.year + 1, month: 0 }
        : { ...current, month: current.month + 1 },
    );
  };

  const goToday = (): void => {
    const now = new Date();
    setCursor({ year: now.getFullYear(), month: now.getMonth() });
    setSelectedDay(todayKey);
  };

  const cells = buildCells(cursor.year, cursor.month);
  const selectedEntries = selectedDay === null ? [] : (byDay.get(selectedDay) ?? []);
  const sortedEntries = sortEntries(selectedEntries);

  return (
    <div className="calendar-view">
      <div className="calendar-header">
        <div className="calendar-nav">
          <button className="icon-button" title="Previous month" onClick={prevMonth}>
            ←
          </button>
          <span className="calendar-title">
            {MONTH_NAMES[cursor.month]} {cursor.year}
          </span>
          <button className="icon-button" title="Next month" onClick={nextMonth}>
            →
          </button>
        </div>
        <button className="button" onClick={goToday}>
          Today
        </button>
      </div>
      <div className="calendar-grid" role="grid">
        {WEEKDAY_LABELS.map((label) => (
          <div className="calendar-weekday" key={label}>
            {label}
          </div>
        ))}
        {cells.map((cell) => {
          const isToday = cell.dayKey !== null && cell.dayKey === todayKey;
          const isSelected = cell.dayKey !== null && cell.dayKey === selectedDay;
          const count = cell.dayKey === null ? 0 : (byDay.get(cell.dayKey)?.length ?? 0);
          const className = [
            "calendar-cell",
            isToday ? "calendar-cell-today" : "",
            isSelected ? "calendar-cell-selected" : "",
          ]
            .filter(Boolean)
            .join(" ");
          return (
            <button
              key={cell.key}
              className={className}
              disabled={cell.dayKey === null}
              onClick={() => cell.dayKey !== null && setSelectedDay(cell.dayKey)}
            >
              <span className="calendar-cell-day">{cell.day ?? ""}</span>
              {count > 0 && <span className="calendar-cell-badge">{count}</span>}
            </button>
          );
        })}
      </div>
      <div className="calendar-day-detail">
        {selectedDay === null ? (
          <p className="dim">Select a day to see the objects dated on it.</p>
        ) : (
          <>
            <div className="calendar-day-title">{friendlyDay(selectedDay)}</div>
            {sortedEntries.length === 0 ? (
              <p className="dim">Nothing dated on this day.</p>
            ) : (
              sortedEntries.map((entry, index) => {
                const type = state.types.find((candidate) => candidate.name === entry.typeName);
                const label = spanLabel(entry.span);
                return (
                  <button
                    key={`${entry.object.uuid}-${entry.span.start}-${index}`}
                    className="calendar-event-row"
                    onClick={() => props.workspace.openObject(entry.object.uuid)}
                  >
                    {type !== undefined && <TypeIcon icon={type.icon} color={type.color} size={14} />}
                    <span className="calendar-event-label">{ObjectLabels.of(entry.object)}</span>
                    <span className="dim">{entry.typeName}</span>
                    {label !== "" && <span className="calendar-event-span dim">{label}</span>}
                  </button>
                );
              })
            )}
          </>
        )}
      </div>
    </div>
  );
}
