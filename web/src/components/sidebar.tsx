import type { ReactElement } from "react";
import { AuthStore } from "../state/auth";
import { useObservable } from "../state/use-observable";
import { WorkspaceStore } from "../state/workspace";
import { ObjectLabels } from "./object-labels";
import { TypeIcon } from "./type-icon";

/** Temporary explorer: every type and every object, flat. */
export function Sidebar(props: {
  workspace: WorkspaceStore;
  auth: AuthStore;
}): ReactElement {
  const state = useObservable(props.workspace);
  const authState = useObservable(props.auth);
  const types = props.workspace.userTypes();

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <span className="brand">nylium</span>
        <button
          className="icon-button"
          title="New type"
          onClick={() => props.workspace.openCreateType()}
        >
          +
        </button>
      </div>
      <nav className="sidebar-scroll">
        <div className="sidebar-section">Types</div>
        {types.map((view) => (
          <div className="type-row" key={view.name}>
            <button
              className="type-row-name"
              onClick={() => props.workspace.openType(view.name)}
            >
              <TypeIcon icon={view.icon} color={view.color} />
              <span>{view.name}</span>
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
        <div className="sidebar-section">Objects</div>
        {state.objects.map((view) => (
          <button
            className="type-row object-entry"
            key={view.uuid}
            title={view.uuid}
            onClick={() => props.workspace.openObject(view.uuid)}
          >
            <span className="type-row-name">{ObjectLabels.of(view)}</span>
            <span className="dim">{view.type_name}</span>
          </button>
        ))}
      </nav>
      <div className="sidebar-footer">
        <span className="sidebar-user">{authState.userName}</span>
        <button
          className="icon-button"
          title="Sign out"
          onClick={() => void props.auth.logout()}
        >
          ⏻
        </button>
      </div>
    </aside>
  );
}
