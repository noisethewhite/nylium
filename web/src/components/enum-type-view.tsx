import type { ReactElement } from "react";
import { useEffect, useState } from "react";
import type { TypeView } from "../contracts";
import { useSaveShortcut } from "../state/use-save-shortcut";
import { usePinTabOnEdit } from "../state/use-pin-tab-on-edit";
import { WorkspaceStore } from "../state/workspace";
import { IconPicker } from "./icon-picker";
import { Table } from "./table";

/** One row of the enum option draft — uuid null marks a not-yet-created
 * option; an existing uuid with a changed value is a rename that the
 * backend propagates into every stored value. */
interface OptionDraft {
  readonly uuid: string | null;
  readonly value: string;
}

function draftsOf(schema: TypeView): OptionDraft[] {
  return schema.enum_options.map((option) => ({
    uuid: option.uuid,
    value: option.value,
  }));
}

/** The enum page: same chrome as the object type page, but the body
 * edits the option list instead of a prop schema. No plural input —
 * enums never name a collection. */
export function EnumTypePanel(props: {
  workspace: WorkspaceStore;
  schema: TypeView;
}): ReactElement {
  const { workspace, schema } = props;
  const [nameDraft, setNameDraft] = useState(schema.name);
  const [iconDraft, setIconDraft] = useState(schema.icon);
  const [colorDraft, setColorDraft] = useState(schema.color);
  const [rows, setRows] = useState<OptionDraft[]>(() => draftsOf(schema));

  useEffect(() => {
    setNameDraft(schema.name);
    setIconDraft(schema.icon);
    setColorDraft(schema.color);
    setRows(draftsOf(schema));
  }, [schema]);

  const updateRow = (index: number, value: string): void => {
    setRows((drafts) =>
      drafts.map((draft, position) =>
        position === index ? { ...draft, value } : draft,
      ),
    );
  };

  const pristine =
    nameDraft === schema.name &&
    iconDraft === schema.icon &&
    colorDraft === schema.color &&
    JSON.stringify(rows) === JSON.stringify(draftsOf(schema));
  const values = rows.map((row) => row.value.trim()).filter((value) => value !== "");
  const invalid =
    nameDraft.trim() === "" || new Set(values).size !== values.length;

  const save = (): void => {
    void workspace.saveEnumEdits(
      schema.name,
      { name: nameDraft.trim(), icon: iconDraft, color: colorDraft },
      rows
        .filter((row) => row.value.trim() !== "")
        .map((row) => ({ uuid: row.uuid, value: row.value.trim() })),
    );
  };
  useSaveShortcut(save, !pristine && !invalid);
  usePinTabOnEdit(workspace, !pristine);

  return (
    <div className="editor-shell">
      <div className="editor-header">
        <span className="dim editor-header-title">Editing enum</span>
        <div className="editor-actions">
          <button
            className="button button-primary"
            disabled={pristine || invalid}
            title={invalid ? "Options must be unique and the name non-empty" : undefined}
            onClick={save}
          >
            Save
          </button>
          <button
            className="button button-danger"
            onClick={() => void workspace.deleteType(schema.name)}
          >
            Delete enum
          </button>
        </div>
      </div>
      <div className="editor-boxes">
        <div className="editor-box">
          <span className="editor-box-label">Enum name</span>
          <div className="editor-box-content">
            <IconPicker
              icon={iconDraft}
              color={colorDraft}
              size={22}
              onChange={(icon, color) => {
                setIconDraft(icon);
                setColorDraft(color);
              }}
            />
            <input
              className="input type-name-input"
              value={nameDraft}
              onChange={(event) => setNameDraft(event.target.value)}
            />
          </div>
        </div>
      </div>
      <Table
        rows={rows}
        keyOf={(row, index) => row.uuid ?? `new-${index}`}
        columns={[
          {
            kind: "string",
            placeholder: "Option",
            value: (row) => row.value,
            onEdit: (row, value, index) => updateRow(index, value),
          },
          {
            kind: "remove",
            title: "Delete option — refused while any value uses it",
            onRemove: (index) =>
              setRows((drafts) => drafts.filter((_, position) => position !== index)),
          },
        ]}
      />
      <div className="editor-footer">
        <button
          className="button"
          onClick={() => setRows((drafts) => [...drafts, { uuid: null, value: "" }])}
        >
          Add Option
        </button>
      </div>
    </div>
  );
}
