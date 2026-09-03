import type { ReactElement } from "react";
import { useState } from "react";
import { TypeNames } from "../contracts";
import { WorkspaceStore } from "../state/workspace";
import { DEFAULT_COLOR, DEFAULT_ICON, IconPicker } from "./icon-picker";
import { TypePicker } from "./type-picker";

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
  const [icon, setIcon] = useState(DEFAULT_ICON);
  const [color, setColor] = useState(DEFAULT_COLOR);
  const [propsDraft, setPropsDraft] = useState<PropDraft[]>([{ ...EMPTY_PROP }]);

  const updateProp = (index: number, patch: Partial<PropDraft>): void => {
    setPropsDraft((drafts) =>
      drafts.map((draft, position) =>
        position === index ? { ...draft, ...patch } : draft,
      ),
    );
  };

  const submit = (): void => {
    // every type opens with the pinned `name` prop — the instance title
    const propsRecord: Record<string, string> = { name: "String" };
    for (const draft of propsDraft) {
      if (draft.key !== "") {
        propsRecord[draft.key] = draft.valueType;
      }
    }
    void props.workspace.createType(name, pluralName, propsRecord, icon, color);
  };

  return (
    <div className="type-create-form">
      <div className="type-header-boxes">
        <div className="type-field-box">
          <span className="type-field-box-label">Type name</span>
          <div className="type-field-box-content">
            <IconPicker
              icon={icon}
              color={color}
              size={22}
              onChange={(nextIcon, nextColor) => {
                setIcon(nextIcon);
                setColor(nextColor);
              }}
            />
            <input
              className="input type-name-input"
              placeholder="Type name"
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </div>
        </div>
        <div className="type-field-box">
          <span className="type-field-box-label">Type plural name</span>
          <div className="type-field-box-content">
            <input
              className="input type-name-input"
              placeholder="Name (plural)"
              value={pluralName}
              onChange={(event) => setPluralName(event.target.value)}
            />
          </div>
        </div>
      </div>
      {/* every type opens with the pinned `name` prop — the instance title */}
      <div className="prop-draft-row prop-draft-row-fixed">
        <span className="schema-prop-key">name</span>
        <span className="dim">String · title</span>
      </div>
      {propsDraft.map((draft, index) => (
        <div className="prop-draft-row" key={index}>
          <input
            className="input"
            placeholder="Property Name"
            value={draft.key}
            onChange={(event) => updateProp(index, { key: event.target.value })}
          />
          <TypePicker
            workspace={props.workspace}
            value={draft.valueType}
            onChange={(valueType) => updateProp(index, { valueType })}
          />
          <button
            className="icon-button"
            title="Remove prop"
            onClick={() =>
              setPropsDraft((drafts) =>
                drafts.filter((_, position) => position !== index),
              )
            }
          >
            ×
          </button>
        </div>
      ))}
      <div className="type-create-actions">
        <button
          className="button"
          onClick={() => setPropsDraft((drafts) => [...drafts, { ...EMPTY_PROP }])}
        >
          Add Property
        </button>
        <button
          className="button button-primary"
          disabled={name === "" || pluralName === ""}
          onClick={submit}
        >
          Create
        </button>
      </div>
    </div>
  );
}
