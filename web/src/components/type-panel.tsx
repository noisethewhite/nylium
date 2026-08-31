import type { ReactElement } from "react";
import { useObservable } from "../state/use-observable";
import { WorkspaceStore } from "../state/workspace";
import { ObjectEditor } from "./object-editor";
import { ObjectLabels } from "./object-labels";

export function TypePanel(props: {
  workspace: WorkspaceStore;
  schema: import("../contracts").TypeView;
}): ReactElement {
  const state = useObservable(props.workspace);

  return (
    <div className="type-panel">
      <header className="type-header">
        <h1>{props.schema.name}</h1>
        <button
          className="button button-primary"
          onClick={() => void props.workspace.createObject()}
        >
          + New {props.schema.name}
        </button>
      </header>
      <div className="type-body">
        <div className="object-list">
          {state.objects.length === 0 && (
            <div className="empty-state">
              <p className="dim">No objects yet.</p>
            </div>
          )}
          {state.objects.map((view) => (
            <button
              key={view.uuid}
              className={
                view.uuid === state.selectedObjectUuid
                  ? "object-row object-row-selected"
                  : "object-row"
              }
              onClick={() => void props.workspace.selectObject(view.uuid)}
            >
              <span className="object-row-label">{ObjectLabels.of(view)}</span>
              <span className="object-row-uuid">{ObjectLabels.shortUuid(view)}</span>
            </button>
          ))}
        </div>
        <ObjectEditor workspace={props.workspace} schema={props.schema} />
      </div>
    </div>
  );
}
