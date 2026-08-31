import type { ReactElement } from "react";
import { useState } from "react";
import { TypeNames } from "../contracts";
import { WorkspaceStore } from "../state/workspace";

interface PropDraft {
  key: string;
  valueType: string;
}

const EMPTY_PROP: PropDraft = { key: "", valueType: TypeNames.STRING };

export function TypeCreateForm(props: {
  workspace: WorkspaceStore;
  onDone: () => void;
}): ReactElement {
  const [name, setName] = useState("");
  const [propsDraft, setPropsDraft] = useState<PropDraft[]>([{ ...EMPTY_PROP }]);

  const typeOptions = TypeNames.SCALARS.flatMap((scalar) => [
    scalar,
    TypeNames.arrayOf(scalar),
  ]).concat(
    props.workspace
      .userTypes()
      .flatMap((view) => [view.name, TypeNames.arrayOf(view.name)]),
  );

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
    void props.workspace.createType(name, propsRecord);
    props.onDone();
  };

  return (
    <div className="type-create-form">
      <input
        className="input"
        placeholder="Type name"
        value={name}
        onChange={(event) => setName(event.target.value)}
      />
      {propsDraft.map((draft, index) => (
        <div className="prop-draft-row" key={index}>
          <input
            className="input"
            placeholder="prop"
            value={draft.key}
            onChange={(event) => updateProp(index, { key: event.target.value })}
          />
          <select
            className="input"
            value={draft.valueType}
            onChange={(event) => updateProp(index, { valueType: event.target.value })}
          >
            {typeOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
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
          + prop
        </button>
        <button
          className="button button-primary"
          disabled={name === ""}
          onClick={submit}
        >
          Create
        </button>
      </div>
    </div>
  );
}
