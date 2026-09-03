import type { ReactElement } from "react";
import { useState } from "react";
import { TypeNames } from "../contracts";
import { WorkspaceStore } from "../state/workspace";
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
  const [propsDraft, setPropsDraft] = useState<PropDraft[]>([{ ...EMPTY_PROP }]);

  const updateProp = (index: number, patch: Partial<PropDraft>): void => {
    setPropsDraft((drafts) =>
      drafts.map((draft, position) =>
        position === index ? { ...draft, ...patch } : draft,
      ),
    );
  };

  const submit = (): void => {
    const propsRecord: Record<string, string> = {};
    for (const draft of propsDraft) {
      if (draft.key !== "") {
        propsRecord[draft.key] = draft.valueType;
      }
    }
    void props.workspace.createType(name, pluralName, propsRecord);
  };

  return (
    <div className="type-create-form">
      <input
        className="input"
        placeholder="Name (singular)"
        value={name}
        onChange={(event) => setName(event.target.value)}
      />
      <input
        className="input"
        placeholder="Name (plural)"
        value={pluralName}
        onChange={(event) => setPluralName(event.target.value)}
      />
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
