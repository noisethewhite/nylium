import type { ChangeEvent, ReactElement } from "react";
import { useEffect, useRef, useState } from "react";
import type { ObjectView, TypeView } from "../contracts";
import { ArrayFieldModel, RefFieldModel } from "../fields/composite-fields";
import { EmbeddedFieldModel } from "../fields/embedded-fields";
import { EnumFieldModel } from "../fields/enum-fields";
import { FileFieldModel } from "../fields/file-fields";
import { CalendarMath, ChipDispatch, DateParsing, NumericFilter } from "./field-editors-logic";
import type { ChipKind } from "./field-editors-logic";
import { FloatingMenu } from "./floating-menu";
import { MONTH_NAMES } from "../month-names";
import { NameSearch } from "./name-search";
import { FieldModel } from "../fields/field-model";
import { UnitDecimalFieldModel } from "../fields/unit-fields";
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
import { TypeIcon } from "./type-icon";
import { TypeName } from "./type-name";

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
  if (field instanceof UnitDecimalFieldModel) {
    return <UnitInput field={field} editor={editor} />;
  }
  if (field instanceof EnumFieldModel) {
    return <EnumInput field={field} editor={editor} />;
  }
  if (field instanceof EmbeddedFieldModel) {
    return <EmbeddedSection field={field} editor={editor} />;
  }
  if (field instanceof FileFieldModel) {
    return <FileInput field={field} editor={editor} />;
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
  return (
    <FieldShell label={props.field.key}>
      <input
        className="input"
        type="text"
        inputMode={props.numeric === "integer" ? "numeric" : "decimal"}
        value={props.field.draft}
        onChange={(event) => {
          props.field.draft = NumericFilter.sanitize(event.target.value, props.numeric);
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

/** Date edited as prose — "August 8, 1995" — while the draft stays
 * canonical "YYYY-MM-DD" for the wire and the regex guard. */
function DateInput({ field, editor }: { field: DateFieldModel; editor: ObjectEditorStore }): ReactElement {
  return (
    <FieldShell label={field.key}>
      <input
        className="input"
        type="text"
        placeholder="August 8, 1995"
        value={DateParsing.formatDraft(field.draft)}
        onChange={(event) => {
          field.draft = DateParsing.parseDateText(event.target.value);
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
  const days = Array.from({ length: CalendarMath.daysInMonth(month) }, (_, index) =>
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
              commit(event.target.value, CalendarMath.clampDay(event.target.value, day), clock)
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

/** Numeric<Unit> editor: the decimal draft input plus a part picker —
 * the number is entered in the picked part, the backend converts into
 * the base part for storage. null unit renders as the base part name. */
function UnitInput(props: {
  field: UnitDecimalFieldModel;
  editor: ObjectEditorStore;
}): ReactElement {
  const { field, editor } = props;

  return (
    <FieldShell
      label={
        <>
          {field.key} → <TypeName workspace={editor.workspace} name={field.valueType} />
        </>
      }
    >
      <div className="field-row">
        <input
          className="input"
          type="text"
          inputMode="decimal"
          value={field.draft}
          onChange={(event) => {
            field.draft = NumericFilter.sanitize(event.target.value, "decimal");
            draftChanged(editor);
          }}
        />
        <FloatingMenu
          wrapperClassName="type-picker"
          triggerClassName="input type-picker-trigger"
          menuClassName="type-menu"
          trigger={
            <>
              <span className="material-symbols-outlined type-picker-chevron" aria-hidden>
                keyboard_arrow_down
              </span>
              <span className="type-picker-value">{field.unit ?? field.base}</span>
            </>
          }
        >
          {(close) => (
            <NameSearch
              items={field.parts}
              getKey={(part) => part}
              getLabel={(part) => part}
              placeholder="Search parts…"
              onPick={(part) => {
                field.unit = part === field.base ? null : part;
                draftChanged(editor);
                close();
              }}
            />
          )}
        </FloatingMenu>
      </div>
      <ErrorPlaque error={field.validationError()} />
    </FieldShell>
  );
}

function EnumInput({ field, editor }: { field: EnumFieldModel; editor: ObjectEditorStore }): ReactElement {
  return (
    <FieldShell
      label={
        <>
          {field.key} → <TypeName workspace={editor.workspace} name={field.valueType} />
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

/** ADR-0004: collapsible inline section for a composition child —
 * the child's own fields render through the same FieldEditor
 * dispatch (recursion covers nested embeds), saving is the parent's
 * single Ctrl+S. The generated child name shows read-only. */
function EmbeddedSection({ field, editor }: { field: EmbeddedFieldModel; editor: ObjectEditorStore }): ReactElement {
  // filled children open expanded; untouched drafts start collapsed
  const [expanded, setExpanded] = useState(field.childUuid !== null);
  const type = editor.typeOf(field.valueType);
  const icon =
    type === undefined ? null : <TypeIcon icon={type.icon} color={type.color} />;
  return (
    <div className="field field-array">
      <span className="field-label">
        {field.key} → <TypeName workspace={editor.workspace} name={field.valueType} />
      </span>
      <div className="field-body">
        <button
          className="input type-picker-trigger embedded-toggle"
          onClick={() => setExpanded((current) => !current)}
        >
          <span className="material-symbols-outlined type-picker-chevron" aria-hidden>
            {expanded ? "expand_more" : "chevron_right"}
          </span>
          {icon}
          <span className="type-picker-value">
            {field.childName ?? (field.childUuid === null ? "—" : field.valueType)}
          </span>
        </button>
        {expanded && (
          <div className="embedded-section">
            {field.childFields.map((child) => (
              <FieldEditor key={child.key} field={child} editor={editor} />
            ))}
            {field.childFields.length === 0 && (
              <span className="dim">No editable props</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function FileInput({ field, editor }: { field: FileFieldModel; editor: ObjectEditorStore }): ReactElement {
  const type = editor.typeOf(field.valueType);
  const icon = type === undefined ? null : <TypeIcon icon={type.icon} color={type.color} />;
  const files = editor.filesOfType(field.valueType);
  const selected = files.find((file) => file.uuid === field.selectedUuid);
  const uploadRef = useRef<HTMLInputElement | null>(null);

  return (
    <FieldShell
      label={
        <>
          {field.key} → <TypeName workspace={editor.workspace} name={field.valueType} />
        </>
      }
    >
      <span className="file-picker-row">
        <FloatingMenu
          wrapperClassName="floating-menu-grow"
          triggerClassName="input type-picker-trigger"
          menuClassName="type-menu"
          trigger={
            <>
              <span className="material-symbols-outlined type-picker-chevron" aria-hidden>
                keyboard_arrow_down
              </span>
              {icon}
              <span className="type-picker-value">
                {selected === undefined ? "—" : selected.name}
              </span>
            </>
          }
        >
          {(close) => (
            <NameSearch
              items={files}
              getKey={(file) => file.uuid}
              getLabel={(file) => file.name}
              renderIcon={() => icon}
              placeholder="Search files…"
              unsetLabel="—"
              onUnset={() => {
                field.selectedUuid = null;
                draftChanged(editor);
                close();
              }}
              onPick={(file) => {
                field.selectedUuid = file.uuid;
                draftChanged(editor);
                close();
              }}
            />
          )}
        </FloatingMenu>
        <button
          className="button"
          type="button"
          title="Upload new file"
          onClick={() => uploadRef.current?.click()}
        >
          Upload
        </button>
        <input
          ref={uploadRef}
          type="file"
          hidden
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file !== undefined) {
              void editor.uploadFileFor(field.valueType, file).then((created) => {
                if (created !== null) {
                  field.selectedUuid = created.uuid;
                  draftChanged(editor);
                }
              });
            }
            event.target.value = "";
          }}
        />
      </span>
    </FieldShell>
  );
}

function RefInput({ field, editor }: { field: RefFieldModel; editor: ObjectEditorStore }): ReactElement {
  const selected = field.options.find((option) => option.uuid === field.selectedUuid);
  const type = editor.typeOf(field.valueType);
  const icon =
    type === undefined ? null : <TypeIcon icon={type.icon} color={type.color} />;
  return (
    <FieldShell
      label={
        <>
          {field.key} → <TypeName workspace={editor.workspace} name={field.valueType} />
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
            {icon}
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
            renderIcon={() => icon}
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
  const chipKind = ChipDispatch.kindOf(field);
  if (chipKind !== null) {
    return <ChipArrayInput field={field} editor={editor} kind={chipKind} />;
  }
  // ADR-0026: an array of embedded objects renders as a table — one column
  // per editable member prop, one row per element — instead of the stacked
  // collapsible cards (which stay for the generic non-embedded case).
  const elementSchema = editor.typeOf(field.elementType);
  if (elementSchema?.embedded) {
    return <EmbeddedTableEditor field={field} editor={editor} schema={elementSchema} />;
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

/** A sortable string for a field: scalar drafts, booleans, ref labels,
 * enum selections. Numeric drafts sort numerically via localeCompare. */
function sortValueOf(field: FieldModel | undefined): string {
  if (field === undefined) {
    return "";
  }
  if (field instanceof ScalarFieldModel) {
    return field.draft;
  }
  if (field instanceof BooleanFieldModel) {
    return field.checked ? "1" : "0";
  }
  if (field instanceof RefFieldModel) {
    const selected = field.options.find((o) => o.uuid === field.selectedUuid);
    return selected !== undefined ? ObjectLabels.of(selected) : "";
  }
  if (field instanceof EnumFieldModel) {
    return field.selected ?? "";
  }
  return "";
}

function compareValues(a: string, b: string): number {
  return a.localeCompare(b, undefined, { numeric: true, sensitivity: "base" });
}

/** ADR-0026: an Array<Embedded> prop edited as a table — columns are the
 * element's editable (non-computed) member props, rows are the elements.
 * Computed members (formula/function/collect) stay out of the editor and
 * render in the read-only object view instead. Columns sort by click and
 * can be hidden via the columns menu. */
function EmbeddedTableEditor({
  field,
  editor,
  schema,
}: {
  field: ArrayFieldModel;
  editor: ObjectEditorStore;
  schema: TypeView;
}): ReactElement {
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [hidden, setHidden] = useState<ReadonlySet<string>>(new Set());

  const allColumns = schema.props.filter(
    (prop) =>
      prop.key !== "name" &&
      prop.formula === null &&
      prop.function_uuid === null &&
      prop.collect === null,
  );
  const columns = allColumns.filter((column) => !hidden.has(column.key));

  const childOf = (item: FieldModel, key: string): FieldModel | undefined =>
    item instanceof EmbeddedFieldModel
      ? item.childFields.find((child) => child.key === key)
      : undefined;

  const applySort = (key: string, dir: "asc" | "desc"): void => {
    editor.sortArrayItems(field, (a, b) => {
      const cmp = compareValues(sortValueOf(childOf(a, key)), sortValueOf(childOf(b, key)));
      return dir === "asc" ? cmp : -cmp;
    });
  };

  const toggleSort = (key: string): void => {
    if (sortColumn !== key) {
      setSortColumn(key);
      setSortDir("asc");
      applySort(key, "asc");
    } else if (sortDir === "asc") {
      setSortDir("desc");
      applySort(key, "desc");
    } else {
      setSortColumn(null);
    }
  };

  const toggleColumn = (key: string): void => {
    const next = new Set(hidden);
    if (next.has(key)) {
      next.delete(key);
    } else {
      next.add(key);
    }
    setHidden(next);
  };

  return (
    <div className="field field-array field-array-table">
      <span className="field-label">
        {field.key} <span className="dim">→ {field.elementType}</span>
      </span>
      <div className="field-body">
        <div className="field-array-head field-array-head-table">
          <button className="button" onClick={() => editor.addArrayItem(field)}>
            + item
          </button>
          <FloatingMenu
            title="Toggle columns"
            triggerClassName="button table-columns-trigger"
            menuClassName="type-menu type-menu-right"
            trigger={
              <span className="material-symbols-outlined" aria-hidden>
                view_column
              </span>
            }
          >
            {() => (
              <div className="column-toggle-menu">
                {allColumns.map((column) => (
                  <label key={column.key} className="column-toggle-row">
                    <input
                      type="checkbox"
                      checked={!hidden.has(column.key)}
                      onChange={() => toggleColumn(column.key)}
                    />
                    <span>{column.key}</span>
                  </label>
                ))}
              </div>
            )}
          </FloatingMenu>
        </div>
        <table className="embedded-table">
          <thead>
            <tr>
              {columns.map((column) => {
                const active = sortColumn === column.key;
                return (
                  <th key={column.key}>
                    <button
                      className="table-sort"
                      onClick={() => toggleSort(column.key)}
                      title={active ? "Clear sort" : "Sort ascending"}
                    >
                      <span>{column.key}</span>
                      {active && (
                        <span className="material-symbols-outlined" aria-hidden>
                          {sortDir === "asc" ? "arrow_upward" : "arrow_downward"}
                        </span>
                      )}
                    </button>
                  </th>
                );
              })}
              <th aria-hidden />
            </tr>
          </thead>
          <tbody>
            {field.items.map((item, index) => {
              const childFields =
                item instanceof EmbeddedFieldModel ? item.childFields : [];
              return (
                <tr key={index}>
                  {columns.map((column) => {
                    const child = childFields.find((c) => c.key === column.key);
                    return (
                      <td key={column.key}>
                        {child !== undefined && (
                          <FieldEditor field={child} editor={editor} />
                        )}
                      </td>
                    );
                  })}
                  <td className="embedded-table-remove">
                    <button
                      className="icon-button"
                      title="Remove item"
                      onClick={() => editor.removeArrayItem(field, index)}
                    >
                      ×
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
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
  const type = editor.typeOf(field.elementType);
  const typeIcon =
    type === undefined ? null : <TypeIcon icon={type.icon} color={type.color} />;
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
              {typeIcon}
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
                  renderIcon={() => typeIcon}
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
