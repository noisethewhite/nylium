/** Business logic behind the field editors — pure functions and
 * dispatchers kept out of the JSX layer so field-editors.tsx stays
 * view-only. Namespace-only, never instantiated (see contracts.ts). */

import { MONTH_NAMES } from "../month-names";
import { ArrayFieldModel, RefFieldModel } from "../fields/composite-fields";
import { EnumFieldModel } from "../fields/enum-fields";
import { FieldFactory } from "../fields/field-factory";

/** Keystroke filter for numeric drafts: only digits, a leading minus
 * and (for decimals) one dot survive — letters and punctuation never
 * land in the draft at all. The regex check still runs on the result,
 * so a draft arriving from a type switch is validated too. */
export abstract class NumericFilter {
  static sanitize(raw: string, kind: "integer" | "decimal"): string {
    const signed = raw.replace(/[^\d.-]/g, "").replace(/(?!^)-/g, "");
    if (kind === "integer") {
      return signed.replace(/\./g, "");
    }
    const [head = "", ...rest] = signed.split(".");
    return rest.length === 0 ? head : `${head}.${rest.join("")}`;
  }
}

/** Date draft parsing: canonical "YYYY-MM-DD" <-> human prose, plus the
 * token grammar a human would type. */
export abstract class DateParsing {
  /** Canonical "YYYY-MM-DD" draft -> "August 8, 1995"; anything else is
   * shown as typed so the user's keystrokes never get eaten. */
  static formatDraft(draft: string): string {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(draft);
    if (match === null) {
      return draft;
    }
    const [, year = "", monthNumber = "", dayNumber = ""] = match;
    const month = MONTH_NAMES[Number.parseInt(monthNumber, 10) - 1] ?? "";
    return `${month} ${Number.parseInt(dayNumber, 10)}, ${year}`;
  }

  /** Resolve a month token — full name or an unambiguous 3+ letter prefix,
   * case-insensitive. Returns the 1-based month number or null. */
  static monthOf(token: string): number | null {
    const needle = token.toLowerCase();
    if (needle.length < 3) {
      return null;
    }
    const index = MONTH_NAMES.findIndex((name) =>
      name.toLowerCase().startsWith(needle),
    );
    return index < 0 ? null : index + 1;
  }

  /** Two-digit years pivot at 50: "95" -> 1995, "05" -> 2005. */
  static fullYear(yearText: string): number {
    const year = Number.parseInt(yearText, 10);
    if (yearText.length !== 2) {
      return year;
    }
    return year < 50 ? 2000 + year : 1900 + year;
  }

  /** Validate and render canonical "YYYY-MM-DD"; null when the date is
   * not real (month 13, February 30, ...). */
  static canonicalDate(year: number, month: number, day: number): string | null {
    if (month < 1 || month > 12 || year < 1) {
      return null;
    }
    const maxDay = new Date(year, month, 0).getDate();
    if (day < 1 || day > maxDay) {
      return null;
    }
    const mm = String(month).padStart(2, "0");
    const dd = String(day).padStart(2, "0");
    return `${String(year).padStart(4, "0")}-${mm}-${dd}`;
  }

  private static readonly MONTH_TOKEN = "[A-Za-z]{3,9}";
  private static readonly ORDINAL = "(?:st|nd|rd|th)?";
  private static readonly YEAR_TOKEN = "(\\d{4}|\\d{2})";

  /** Typed text -> canonical draft. Accepts about anything a human would
   * call a date and converts it on the spot:
   *   "1995-08-08" / "1995/8/8"     ISO-ish, year first
   *   "August 8, 1995" / "Aug 8 95" prose, month first
   *   "8 August 1995" / "8th Aug 95" prose, day first
   *   "8/8/1995" / "08.08.95"       numeric, day-first (a > 12 or b > 12
   *                                 disambiguates either way)
   * Unparseable text passes through raw so the user's keystrokes are
   * never eaten and the regex plaque can explain what went wrong. */
  static parseDateText(text: string): string {
    const trimmed = text.trim();

    // year first: 1995-08-08, 1995/8/8, 1995.8.8
    let match = /^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$/.exec(trimmed);
    if (match !== null) {
      const parsed = DateParsing.canonicalDate(
        Number(match[1]),
        Number(match[2]),
        Number(match[3]),
      );
      return parsed ?? text;
    }

    // prose, month first: August 8, 1995 / Aug 8th 95
    match = new RegExp(
      `^(${DateParsing.MONTH_TOKEN})\\s+(\\d{1,2})${DateParsing.ORDINAL},?\\s+${DateParsing.YEAR_TOKEN}$`,
      "i",
    ).exec(trimmed);
    if (match !== null) {
      const month = DateParsing.monthOf(match[1] ?? "");
      const parsed =
        month === null
          ? null
          : DateParsing.canonicalDate(
              DateParsing.fullYear(match[3] ?? ""),
              month,
              Number(match[2]),
            );
      return parsed ?? text;
    }

    // prose, day first: 8 August 1995 / 8th Aug, 95
    match = new RegExp(
      `^(\\d{1,2})${DateParsing.ORDINAL}\\s+(${DateParsing.MONTH_TOKEN}),?\\s+${DateParsing.YEAR_TOKEN}$`,
      "i",
    ).exec(trimmed);
    if (match !== null) {
      const month = DateParsing.monthOf(match[2] ?? "");
      const parsed =
        month === null
          ? null
          : DateParsing.canonicalDate(
              DateParsing.fullYear(match[3] ?? ""),
              month,
              Number(match[1]),
            );
      return parsed ?? text;
    }

    // numeric: 8/8/1995, 08.08.95 — a > 12 or b > 12 decides the order,
    // otherwise day-first (the user writes European dates)
    match = /^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2}|\d{4})$/.exec(trimmed);
    if (match !== null) {
      const a = Number(match[1]);
      const b = Number(match[2]);
      const year = DateParsing.fullYear(match[3] ?? "");
      const [day, month] = a > 12 ? [a, b] : b > 12 ? [b, a] : [a, b];
      const parsed = DateParsing.canonicalDate(year, month, day);
      return parsed ?? text;
    }

    return text;
  }
}

/** Calendar arithmetic for year-less dates (MonthDay / MonthDayTime). */
export abstract class CalendarMath {
  /** Leap-year based day count — year-less dates may be Feb 29. */
  static daysInMonth(month: string): number {
    const index = Number.parseInt(month, 10);
    if (Number.isNaN(index)) {
      return 31;
    }
    return new Date(2000, index, 0).getDate();
  }

  static clampDay(month: string, day: string): string {
    const max = CalendarMath.daysInMonth(month);
    if (day === "" || Number.parseInt(day, 10) <= max) {
      return day;
    }
    return String(max).padStart(2, "0");
  }
}

/** Kind of array element that renders as token chips. */
export type ChipKind = "ref" | "enum";

/** Arrays of refs/enums render as token chips; scalar arrays keep rows. */
export abstract class ChipDispatch {
  static kindOf(field: ArrayFieldModel): ChipKind | null {
    const probe =
      field.items[0] ??
      FieldFactory.createForType(
        field.key,
        field.elementType,
        undefined,
        field.enumOptionsOf,
        field.unitPartsOf,
        field.embeddedSchemaOf,
      );
    if (probe instanceof RefFieldModel) {
      return "ref";
    }
    if (probe instanceof EnumFieldModel) {
      return "enum";
    }
    return null;
  }
}
