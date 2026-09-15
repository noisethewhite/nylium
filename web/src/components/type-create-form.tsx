import type { ReactElement } from "react";
import { useState } from "react";
import { TypeNames } from "../contracts";
import { pluralize } from "../pluralize";
import { WorkspaceStore } from "../state/workspace";
import { DEFAULT_COLOR, DEFAULT_ICON, IconPicker } from "./icon-picker";
import { Table } from "./table";

interface PropDraft {
  key: string;
  valueType: string;
}

const EMPTY_PROP: PropDraft = { key: "", valueType: TypeNames.STRING };

export function TypeCreateForm(props: {
  workspace: WorkspaceStore;
}): ReactElement {
  const [name, setName] = useState("");
  const [pluralName, setPluralName] = useState("");
  // plural auto-follows the singular via `pluralize` until the user
  // edits it by hand — after that the manual value wins
  const [pluralTouched, setPluralTouched] = useState(false);
  const [icon, setIcon] = useState(DEFAULT_ICON);
  const [color, setColor] = useState(DEFAULT_COLOR);
  const [propsDraft, setPropsDraft] = useState<PropDraft[]>([{ ...EMPTY_PROP }]);
  // ADR-0004: composition type — instances live only as prop values
  const [embedded, setEmbedded] = useState(false);

  const updateProp = (index: number, patch: Partial<PropDraft>): void => {
    setPropsDraft((drafts) =>
      drafts.map((draft, position) =>
        position === index ? { ...draft, ...patch } : draft,
      ),
    );
  };

  const submit = (): void => {
    // stray whitespace around names must not reach the backend
    const typeName = name.trim();
    // an emptied manual plural falls back to the generated guess —
    // never ship "" to the backend
    const typePlural = pluralName.trim() || pluralize(typeName);
    // every type opens with the pinned `name` prop — the instance title
    const propsRecord: Record<string, string> = { name: "String" };
    for (const draft of propsDraft) {
      const key = draft.key.trim();
      if (key !== "") {
        propsRecord[key] = draft.valueType;
      }
    }
    void props.workspace.createType(typeName, typePlural, propsRecord, icon, color, embedded);
  };

  return (
    <div className="type-create-form">
      <div className="editor-boxes">
        <div className="editor-box">
          <span className="editor-box-label">Type name</span>
          <div className="editor-box-content">
            <IconPicker
              icon={icon}
              color={color}
              size={22}
              onUploadImage={(file) => props.workspace.uploadIconImage(file)}
              onChange={(nextIcon, nextColor) => {
                setIcon(nextIcon);
                setColor(nextColor);
              }}
            />
            <input
              className="input type-name-input"
              placeholder="Type name"
              value={name}
              onChange={(event) => {
                const next = event.target.value;
                setName(next);
                if (!pluralTouched) {
                  setPluralName(pluralize(next));
                }
              }}
            />
          </div>
        </div>
        <div className="editor-box">
          <span className="editor-box-label">Type plural name</span>
          <div className="editor-box-content">
            <input
              className="input type-name-input"
              placeholder="Name (plural)"
              value={pluralName}
              onChange={(event) => {
                setPluralTouched(true);
                setPluralName(event.target.value);
              }}
            />
          </div>
        </div>
      </div>
      {/* every type opens with the pinned `name` prop — the instance title */}
      <Table
        rows={[{ key: "name", valueType: TypeNames.STRING }, ...propsDraft]}
        keyOf={(row, index) => (index === 0 ? "fixed-name" : `draft-${index}`)}
        locked={(row, index) => index === 0}
        columns={[
          {
            kind: "string",
            placeholder: "Property Name",
            value: (row) => row.key,
            onEdit: (row, value, index) => updateProp(index - 1, { key: value }),
          },
          {
            kind: "type-selector",
            workspace: props.workspace,
            value: (row) => row.valueType,
            display: (row, index) =>
              index === 0 ? <span className="dim">String · title</span> : undefined,
            onPick: (row, value, index) => updateProp(index - 1, { valueType: value }),
          },
          {
            kind: "remove",
            title: "Remove prop",
            visible: (row, index) => index > 0,
            onRemove: (index) =>
              setPropsDraft((drafts) =>
                drafts.filter((_, position) => position !== index - 1),
              ),
          },
        ]}
      />
      <div className="editor-footer">
        <label className="embedded-checkbox">
          <input
            type="checkbox"
            checked={embedded}
            onChange={(event) => setEmbedded(event.target.checked)}
          />
          Embedded — instances exist only as a property value
        </label>
        <button
          className="button"
          onClick={() => setPropsDraft((drafts) => [...drafts, { ...EMPTY_PROP }])}
        >
          Add Property
        </button>
        <button
          className="button button-primary"
          disabled={name.trim() === ""}
          onClick={submit}
        >
          Create
        </button>
      </div>
    </div>
  );
}
