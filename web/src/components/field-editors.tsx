import type { ChangeEvent, ReactElement } from "react";
import { ArrayFieldModel, RefFieldModel } from "../fields/composite-fields";
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

function TextInput({ field, editor }: { field: TextFieldModel; editor: ObjectEditorStore }): ReactElement {
  return (
    <label className="field">
      <span className="field-label">{field.key}</span>
      <input
        className="input"
        value={field.draft}
        onChange={(event) => {
          field.draft = event.target.value;
          draftChanged(editor);
        }}
      />
      <ErrorPlaque error={field.validationError()} />
    </label>
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
    <label className="field">
      <span className="field-label">{props.field.key}</span>
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
    </label>
  );
}

function DatetimeInput({ field, editor }: { field: DatetimeFieldModel; editor: ObjectEditorStore }): ReactElement {
  return (
    <label className="field">
      <span className="field-label">{field.key}</span>
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
    </label>
  );
}

function DateInput({ field, editor }: { field: DateFieldModel; editor: ObjectEditorStore }): ReactElement {
  return (
    <label className="field">
      <span className="field-label">{field.key}</span>
      <input
        className="input"
        type="date"
        value={field.draft}
        onChange={(event) => {
          field.draft = event.target.value;
          draftChanged(editor);
        }}
      />
      <ErrorPlaque error={field.validationError()} />
    </label>
  );
}

function TimeInput({ field, editor }: { field: TimeFieldModel; editor: ObjectEditorStore }): ReactElement {
  return (
    <label className="field">
      <span className="field-label">{field.key}</span>
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
    </label>
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
  );
}

function BooleanInput({ field, editor }: { field: BooleanFieldModel; editor: ObjectEditorStore }): ReactElement {
  return (
    <label className="field field-inline">
      <span className="field-label">{field.key}</span>
      <input
        type="checkbox"
        checked={field.checked}
        onChange={(event: ChangeEvent<HTMLInputElement>) => {
          field.checked = event.target.checked;
          draftChanged(editor);
        }}
      />
    </label>
  );
}

function RefInput({ field, editor }: { field: RefFieldModel; editor: ObjectEditorStore }): ReactElement {
  return (
    <label className="field">
      <span className="field-label">
        {field.key} <span className="dim">→ {field.valueType}</span>
      </span>
      <select
        className="input"
        value={field.selectedUuid ?? ""}
        onChange={(event) => {
          field.selectedUuid = event.target.value === "" ? null : event.target.value;
          draftChanged(editor);
        }}
      >
        <option value="">—</option>
        {field.options.map((option) => (
          <option key={option.uuid} value={option.uuid}>
            {ObjectLabels.of(option)}
          </option>
        ))}
      </select>
    </label>
  );
}

function ArrayEditor({ field, editor }: { field: ArrayFieldModel; editor: ObjectEditorStore }): ReactElement {
  return (
    <div className="field field-array">
      <div className="field-array-head">
        <span className="field-label">
          {field.key} <span className="dim">→ {field.elementType}</span>
        </span>
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
  );
}
