import type { ChangeEvent, ReactElement } from "react";
import { ArrayFieldModel, RefFieldModel } from "../fields/composite-fields";
import { FieldModel } from "../fields/field-model";
import {
  BooleanFieldModel,
  DatetimeFieldModel,
  DecimalFieldModel,
  IntegerFieldModel,
  ScalarFieldModel,
  TextFieldModel,
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
    return <DraftInput field={field} editor={editor} step="1" />;
  }
  if (field instanceof DecimalFieldModel) {
    return <DraftInput field={field} editor={editor} step="any" />;
  }
  if (field instanceof BooleanFieldModel) {
    return <BooleanInput field={field} editor={editor} />;
  }
  if (field instanceof DatetimeFieldModel) {
    return <DatetimeInput field={field} editor={editor} />;
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
    </label>
  );
}

function DraftInput(props: {
  field: ScalarFieldModel;
  editor: ObjectEditorStore;
  step: string;
}): ReactElement {
  return (
    <label className="field">
      <span className="field-label">{props.field.key}</span>
      <input
        className="input"
        type="number"
        step={props.step}
        value={props.field.draft}
        onChange={(event) => {
          props.field.draft = event.target.value;
          draftChanged(props.editor);
        }}
      />
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
    </label>
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
