import type { ReactElement } from "react";
import { useState } from "react";
import { useObservable } from "../state/use-observable";
import { WorkspaceStore } from "../state/workspace";
import { TypeCreateForm } from "./type-create-form";

export function Sidebar(props: { workspace: WorkspaceStore }): ReactElement {
  const state = useObservable(props.workspace);
  const [creating, setCreating] = useState(false);
  const types = props.workspace.userTypes();

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <span className="brand">nylium</span>
        <button
          className="icon-button"
          title="New type"
          onClick={() => setCreating((open) => !open)}
        >
          +
        </button>
      </div>
      {creating && (
        <TypeCreateForm
          workspace={props.workspace}
          onDone={() => setCreating(false)}
        />
      )}
      <nav className="type-list">
        {types.map((view) => (
          <div
            key={view.name}
            className={
              view.name === state.selectedTypeName
                ? "type-row type-row-selected"
                : "type-row"
            }
          >
            <button
              className="type-row-name"
              onClick={() => void props.workspace.selectType(view.name)}
            >
              {view.name}
            </button>
            <button
              className="icon-button type-row-delete"
              title={`Delete type ${view.name}`}
              onClick={() => void props.workspace.deleteType(view.name)}
            >
              ×
            </button>
          </div>
        ))}
      </nav>
    </aside>
  );
}
