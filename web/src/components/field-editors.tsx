import type { ChangeEvent, ReactElement } from "react";
import { useEffect, useState } from "react";
import type { ObjectView } from "../contracts";
import { ArrayFieldModel, RefFieldModel } from "../fields/composite-fields";
import { EnumFieldModel } from "../fields/enum-fields";
import { FieldFactory } from "../fields/field-factory";
import { FloatingMenu } from "./floating-menu";
import { NameSearch } from "./name-search";
import { FieldModel } from "../fields/field-model";
import {
  BooleanFieldModel,
  DateFieldModel,
  DatetimeFieldModel,
  DecimalFieldModel,
  IntegerFieldModel,
  MonthDayFieldModel,
  MonthDayTimeFieldModel,
  ScalarFieldModel,
  TextFieldModel,
  TimeFieldModel,
} from "../fields/scalar-fields";
import { ObjectEditorStore } from "../state/object-editor";
import { ObjectLabels } from "./object-labels";

interface FieldProps {
  field: FieldModel;
  editor: ObjectEditorStore;
}

/** Renders the control matching each FieldModel kind — the closed
 * hierarchy makes this an instanceof dispatch. */
export function FieldEditor({ field, editor }: FieldProps): ReactElement {
  if (field instanceof TextFieldModel) {
    return <TextInput field={field} editor={editor} />;
  }
  if (field instanceof IntegerFieldModel) {
    return <DraftInput field={field} editor={editor} numeric="integer" />;
  }
  if (field instanceof DecimalFieldModel) {
    return <DraftInput field={field} editor={editor} numeric="decimal" />;
  }
  if (field instanceof BooleanFieldModel) {
    return <BooleanInput field={field} editor={editor} />;
  }
  if (field instanceof DatetimeFieldModel) {
    return <DatetimeInput field={field} editor={editor} />;
  }
  if (field instanceof DateFieldModel) {
    return <DateInput field={field} editor={editor} />;
  }
  if (field instanceof TimeFieldModel) {
    return <TimeInput field={field} editor={editor} />;
  }
  if (field instanceof MonthDayTimeFieldModel) {
    return <MonthDayInput field={field} editor={editor} withTime />;
  }
  if (field instanceof MonthDayFieldModel) {
    return <MonthDayInput field={field} editor={editor} withTime={false} />;
  }
  if (field instanceof EnumFieldModel) {
    return <EnumInput field={field} editor={editor} />;
  }
  if (field instanceof RefFieldModel) {
    return <RefInput field={field} editor={editor} />;
  }
  if (field instanceof ArrayFieldModel) {
    return <ArrayEditor field={field} editor={editor} />;
  }
  throw new Error(`no editor for field kind ${field.constructor.name}`);
}

function draftChanged(editor: ObjectEditorStore): void {
  editor.touch();
}

/** Red plaque under a field whose draft breaks its regex. */
function ErrorPlaque({ error }: { error: string | null }): ReactElement | null {
  if (error === null) {
    return null;
  }
  return <div className="field-error">{error}</div>;
}

/** Field chrome shared by every editor: grey label pinned left (the
 * MoreButtons layout), control + error plaque stacked on the right. */
function FieldShell(props: {
  label: ReactElement | string;
  children: ReactElement | (ReactElement | null)[];
}): ReactElement {
  return (
    <label className="field">
      <span className="field-label">{props.label}</span>
      <span className="field-body">{props.children}</span>
    </label>
  );
}

function TextInput({ field, editor }: { field: TextFieldModel; editor: ObjectEditorStore }): ReactElement {
  return (
    <FieldShell label={field.key}>
      <input
        className="input"
        value={field.draft}
        onChange={(event) => {
          field.draft = event.target.value;
          draftChanged(editor);
        }}
      />
      <ErrorPlaque error={field.validationError()} />
    </FieldShell>
  );
}

/** Text input with keystroke filtering for numeric fields: letters and
 * punctuation never land in the draft at all, only digits, a leading
 * minus and (for decimals) one dot do. The regex check still runs on
 * the result, so a draft arriving from a type switch is validated too. */
function DraftInput(props: {
  field: ScalarFieldModel;
  editor: ObjectEditorStore;
  numeric: "integer" | "decimal";
}): ReactElement {
  const numericFilter = (raw: string): string => {
    const signed = raw.replace(/[^\d.-]/g, "").replace(/(?!^)-/g, "");
    if (props.numeric === "integer") {
      return signed.replace(/\./g, "");
    }
    const [head = "", ...rest] = signed.split(".");
    return rest.length === 0 ? head : `${head}.${rest.join("")}`;
  };

  return (
    <FieldShell label={props.field.key}>
      <input
        className="input"
        type="text"
        inputMode={props.numeric === "integer" ? "numeric" : "decimal"}
        value={props.field.draft}
        onChange={(event) => {
          props.field.draft = numericFilter(event.target.value);
          draftChanged(props.editor);
        }}
      />
      <ErrorPlaque error={props.field.validationError()} />
    </FieldShell>
  );
}

function DatetimeInput({ field, editor }: { field: DatetimeFieldModel; editor: ObjectEditorStore }): ReactElement {
  return (
    <FieldShell label={field.key}>
      <input
        className="input"
        type="datetime-local"
        value={field.draft}
        onChange={(event) => {
          field.draft = event.target.value;
          draftChanged(editor);
        }}
      />
      <ErrorPlaque error={field.validationError()} />
    </FieldShell>
  );
}

const MONTH_NAMES = [
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

/** Canonical "YYYY-MM-DD" draft -> "August 8, 1995"; anything else is
 * shown as typed so the user's keystrokes never get eaten. */
function formatDateDraft(draft: string): string {
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
function monthOf(token: string): number | null {
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
function fullYear(yearText: string): number {
  const year = Number.parseInt(yearText, 10);
  if (yearText.length !== 2) {
    return year;
  }
  return year < 50 ? 2000 + year : 1900 + year;
}

/** Validate and render canonical "YYYY-MM-DD"; null when the date is
 * not real (month 13, February 30, ...). */
function canonicalDate(year: number, month: number, day: number): string | null {
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

const MONTH_TOKEN = "[A-Za-z]{3,9}";
const ORDINAL = "(?:st|nd|rd|th)?";
const YEAR_TOKEN = "(\\d{4}|\\d{2})";

/** Typed text -> canonical draft. Accepts about anything a human would
 * call a date and converts it on the spot:
 *   "1995-08-08" / "1995/8/8"     ISO-ish, year first
 *   "August 8, 1995" / "Aug 8 95" prose, month first
 *   "8 August 1995" / "8th Aug 95" prose, day first
 *   "8/8/1995" / "08.08.95"       numeric, day-first (a > 12 or b > 12
 *                                 disambiguates either way)
 * Unparseable text passes through raw so the user's keystrokes are
 * never eaten and the regex plaque can explain what went wrong. */
export function parseDateText(text: string): string {
  const trimmed = text.trim();

  // year first: 1995-08-08, 1995/8/8, 1995.8.8
  let match = /^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$/.exec(trimmed);
  if (match !== null) {
    const parsed = canonicalDate(Number(match[1]), Number(match[2]), Number(match[3]));
    return parsed ?? text;
  }

  // prose, month first: August 8, 1995 / Aug 8th 95
  match = new RegExp(
    `^(${MONTH_TOKEN})\\s+(\\d{1,2})${ORDINAL},?\\s+${YEAR_TOKEN}$`,
    "i",
  ).exec(trimmed);
  if (match !== null) {
    const month = monthOf(match[1] ?? "");
    const parsed =
      month === null
        ? null
        : canonicalDate(fullYear(match[3] ?? ""), month, Number(match[2]));
    return parsed ?? text;
  }

  // prose, day first: 8 August 1995 / 8th Aug, 95
  match = new RegExp(
    `^(\\d{1,2})${ORDINAL}\\s+(${MONTH_TOKEN}),?\\s+${YEAR_TOKEN}$`,
    "i",
  ).exec(trimmed);
  if (match !== null) {
    const month = monthOf(match[2] ?? "");
    const parsed =
      month === null
        ? null
        : canonicalDate(fullYear(match[3] ?? ""), month, Number(match[1]));
    return parsed ?? text;
  }

  // numeric: 8/8/1995, 08.08.95 — a > 12 or b > 12 decides the order,
  // otherwise day-first (the user writes European dates)
  match = /^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2}|\d{4})$/.exec(trimmed);
  if (match !== null) {
    const a = Number(match[1]);
    const b = Number(match[2]);
    const year = fullYear(match[3] ?? "");
    const [day, month] = a > 12 ? [a, b] : b > 12 ? [b, a] : [a, b];
    const parsed = canonicalDate(year, month, day);
    return parsed ?? text;
  }

  return text;
}

/** Date edited as prose — "August 8, 1995" — while the draft stays
 * canonical "YYYY-MM-DD" for the wire and the regex guard. */
function DateInput({ field, editor }: { field: DateFieldModel; editor: ObjectEditorStore }): ReactElement {
  return (
    <FieldShell label={field.key}>
      <input
        className="input"
        type="text"
        placeholder="August 8, 1995"
        value={formatDateDraft(field.draft)}
        onChange={(event) => {
          field.draft = parseDateText(event.target.value);
          draftChanged(editor);
        }}
      />
      <ErrorPlaque error={field.validationError()} />
    </FieldShell>
  );
}

function TimeInput({ field, editor }: { field: TimeFieldModel; editor: ObjectEditorStore }): ReactElement {
  return (
    <FieldShell label={field.key}>
      <input
        className="input"
        type="time"
        value={field.draft}
        onChange={(event) => {
          field.draft = event.target.value;
          draftChanged(editor);
        }}
      />
      <ErrorPlaque error={field.validationError()} />
    </FieldShell>
  );
}

/** Leap-year based day count — year-less dates may be Feb 29. */
function daysInMonth(month: string): number {
  const index = Number.parseInt(month, 10);
  if (Number.isNaN(index)) {
    return 31;
  }
  return new Date(2000, index, 0).getDate();
}

function clampDay(month: string, day: string): string {
  const max = daysInMonth(month);
  if (day === "" || Number.parseInt(day, 10) <= max) {
    return day;
  }
  return String(max).padStart(2, "0");
}

/** Year-less date editor: month/day selects, optionally a time input.
 * The draft keeps the raw "MM-DD[T]HH:MM" stamp; an incomplete
 * selection stays in the draft, fails the regex and shows the plaque. */
function MonthDayInput(props: {
  field: MonthDayFieldModel | MonthDayTimeFieldModel;
  editor: ObjectEditorStore;
  withTime: boolean;
}): ReactElement {
  const [stamp = "", clock = ""] = props.field.draft.split("T");
  const [month = "", day = ""] = stamp.split("-");
  const days = Array.from({ length: daysInMonth(month) }, (_, index) =>
    String(index + 1).padStart(2, "0"),
  );

  const commit = (nextMonth: string, nextDay: string, nextClock: string): void => {
    if (nextMonth === "" && nextDay === "" && nextClock === "") {
      props.field.draft = "";
    } else if (props.withTime) {
      props.field.draft = `${nextMonth}-${nextDay}T${nextClock}`;
    } else {
      props.field.draft = `${nextMonth}-${nextDay}`;
    }
    draftChanged(props.editor);
  };

  return (
    <div className="field">
      <span className="field-label">{props.field.key}</span>
      <div className="field-body">
        <div className="field-row">
          <select
            className="input"
            value={month}
            onChange={(event) =>
              commit(event.target.value, clampDay(event.target.value, day), clock)
            }
          >
            <option value="">month</option>
            {MONTH_NAMES.map((name, index) => (
              <option key={name} value={String(index + 1).padStart(2, "0")}>
                {name}
              </option>
            ))}
          </select>
          <select
            className="input"
            value={day}
            onChange={(event) => commit(month, event.target.value, clock)}
          >
            <option value="">day</option>
            {days.map((value) => (
              <option key={value} value={value}>
                {Number.parseInt(value, 10)}
              </option>
            ))}
          </select>
          {props.withTime && (
            <input
              className="input"
              type="time"
              value={clock}
              onChange={(event) => commit(month, day, event.target.value)}
            />
          )}
        </div>
        <ErrorPlaque error={props.field.validationError()} />
      </div>
    </div>
  );
}

function BooleanInput({ field, editor }: { field: BooleanFieldModel; editor: ObjectEditorStore }): ReactElement {
  return (
    <FieldShell label={field.key}>
      <input
        type="checkbox"
        checked={field.checked}
        onChange={(event: ChangeEvent<HTMLInputElement>) => {
          field.checked = event.target.checked;
          draftChanged(editor);
        }}
      />
    </FieldShell>
  );
}

function EnumInput({ field, editor }: { field: EnumFieldModel; editor: ObjectEditorStore }): ReactElement {
  return (
    <FieldShell
      label={
        <>
          {field.key} <span className="dim">→ {field.valueType}</span>
        </>
      }
    >
      <FloatingMenu
        wrapperClassName="floating-menu-grow"
        triggerClassName="input type-picker-trigger"
        menuClassName="type-menu"
        trigger={
          <>
            <span className="material-symbols-outlined type-picker-chevron" aria-hidden>
              keyboard_arrow_down
            </span>
            <span className="type-picker-value">{field.selected ?? "—"}</span>
          </>
        }
      >
        {(close) => (
          <NameSearch
            items={field.options}
            getKey={(option) => option}
            getLabel={(option) => option}
            placeholder="Search options…"
            unsetLabel="—"
            onUnset={() => {
              field.selected = null;
              draftChanged(editor);
              close();
            }}
            onPick={(option) => {
              field.selected = option;
              draftChanged(editor);
              close();
            }}
          />
        )}
      </FloatingMenu>
    </FieldShell>
  );
}

function RefInput({ field, editor }: { field: RefFieldModel; editor: ObjectEditorStore }): ReactElement {
  const selected = field.options.find((option) => option.uuid === field.selectedUuid);
  return (
    <FieldShell
      label={
        <>
          {field.key} <span className="dim">→ {field.valueType}</span>
        </>
      }
    >
      <FloatingMenu
        wrapperClassName="floating-menu-grow"
        triggerClassName="input type-picker-trigger"
        menuClassName="type-menu"
        trigger={
          <>
            <span className="material-symbols-outlined type-picker-chevron" aria-hidden>
              keyboard_arrow_down
            </span>
            <span className="type-picker-value">
              {selected === undefined ? "—" : ObjectLabels.of(selected)}
            </span>
          </>
        }
      >
        {(close) => (
          <NameSearch
            items={field.options}
            getKey={(option) => option.uuid}
            getLabel={(option) => ObjectLabels.of(option)}
            placeholder="Search objects…"
            unsetLabel="—"
            onUnset={() => {
              field.selectedUuid = null;
              draftChanged(editor);
              close();
            }}
            onPick={(option) => {
              field.selectedUuid = option.uuid;
              draftChanged(editor);
              close();
            }}
          />
        )}
      </FloatingMenu>
    </FieldShell>
  );
}

function ArrayEditor({ field, editor }: { field: ArrayFieldModel; editor: ObjectEditorStore }): ReactElement {
  const chipKind = chipKindOf(field);
  if (chipKind !== null) {
    return <ChipArrayInput field={field} editor={editor} kind={chipKind} />;
  }
  return (
    <div className="field field-array">
      <span className="field-label">
        {field.key} <span className="dim">→ {field.elementType}</span>
      </span>
      <div className="field-body">
        <div className="field-array-head">
          <button className="button" onClick={() => editor.addArrayItem(field)}>
            + item
          </button>
        </div>
        {field.items.map((item, index) => (
          <div className="field-array-item" key={index}>
            <div className="field-array-item-editor">
              <FieldEditor field={item} editor={editor} />
            </div>
            <button
              className="icon-button"
              title="Remove item"
              onClick={() => editor.removeArrayItem(field, index)}
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

type ChipKind = "ref" | "enum";

/** Arrays of refs/enums render as token chips; scalar arrays keep rows. */
function chipKindOf(field: ArrayFieldModel): ChipKind | null {
  const probe =
    field.items[0] ??
    FieldFactory.createForType(field.key, field.elementType, undefined, field.enumOptionsOf);
  if (probe instanceof RefFieldModel) {
    return "ref";
  }
  if (probe instanceof EnumFieldModel) {
    return "enum";
  }
  return null;
}

/** Email-recipient style editor: picked values become oval chips with a
 * remove ×, adding goes through the shared NameSearch. */
function ChipArrayInput({
  field,
  editor,
  kind,
}: {
  field: ArrayFieldModel;
  editor: ObjectEditorStore;
  kind: ChipKind;
}): ReactElement {
  const [refOptions, setRefOptions] = useState<readonly ObjectView[]>([]);
  useEffect(() => {
    if (kind !== "ref") {
      return;
    }
    let alive = true;
    void editor.refOptionsOf(field.elementType).then((options) => {
      if (alive) {
        setRefOptions(options);
      }
    });
    return () => {
      alive = false;
    };
  }, [editor, field.elementType, kind]);

  const enumOptions =
    kind === "enum" ? (field.enumOptionsOf?.(field.elementType) ?? []) : [];
  const takenUuids = new Set(
    field.items.map((item) => (item instanceof RefFieldModel ? item.selectedUuid : null)),
  );
  const takenOptions = new Set(
    field.items.map((item) => (item instanceof EnumFieldModel ? item.selected : null)),
  );

  const labelOf = (item: FieldModel): string => {
    if (item instanceof RefFieldModel) {
      const found = refOptions.find((option) => option.uuid === item.selectedUuid);
      if (found !== undefined) {
        return ObjectLabels.of(found);
      }
      return item.selectedUuid?.slice(0, 8) ?? "—";
    }
    if (item instanceof EnumFieldModel) {
      return item.selected ?? "—";
    }
    return "?";
  };

  const addPick = (pick: ObjectView | string): void => {
    const item = field.addItem();
    if (item instanceof RefFieldModel && typeof pick !== "string") {
      item.selectedUuid = pick.uuid;
    }
    if (item instanceof EnumFieldModel && typeof pick === "string") {
      item.selected = pick;
    }
    editor.touch();
  };

  return (
    <div className="field field-array">
      <span className="field-label">
        {field.key} <span className="dim">→ {field.elementType}</span>
      </span>
      <div className="field-body">
        <div className="chip-field">
          {field.items.map((item, index) => (
            <span className="chip" key={index}>
              {labelOf(item)}
              <button
                className="chip-remove"
                title="Remove"
                onClick={() => editor.removeArrayItem(field, index)}
              >
                ×
              </button>
            </span>
          ))}
          <FloatingMenu
            wrapperClassName="chip-add"
            triggerClassName="chip chip-add-trigger"
            menuClassName="type-menu"
            title={`Add ${field.elementType}`}
            trigger={<span className="dim">+</span>}
          >
            {(close) =>
              kind === "ref" ? (
                <NameSearch
                  items={refOptions.filter((option) => !takenUuids.has(option.uuid))}
                  getKey={(option) => option.uuid}
                  getLabel={(option) => ObjectLabels.of(option)}
                  placeholder="Search objects…"
                  onPick={(option) => {
                    addPick(option);
                    close();
                  }}
                />
              ) : (
                <NameSearch
                  items={enumOptions.filter((option) => !takenOptions.has(option))}
                  getKey={(option) => option}
                  getLabel={(option) => option}
                  placeholder="Search options…"
                  onPick={(option) => {
                    addPick(option);
                    close();
                  }}
                />
              )
            }
          </FloatingMenu>
        </div>
      </div>
    </div>
  );
}
