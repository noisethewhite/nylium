import type { ReactElement } from "react";
import { useState } from "react";
import { AuthStore } from "../state/auth";
import { useObservable } from "../state/use-observable";
import { WorkspaceStore } from "../state/workspace";
import { ObjectLabels } from "./object-labels";
import { TypeIcon } from "./type-icon";

/** What the "+" popover is showing: the root menu or the pick-a-type
 * list that "New object" expands into. */
type PlusMenuMode = "root" | "object";

/** Temporary explorer: every type and every object, flat. */
export function Sidebar(props: {
  workspace: WorkspaceStore;
  auth: AuthStore;
}): ReactElement {
  const state = useObservable(props.workspace);
  const authState = useObservable(props.auth);
  const types = props.workspace.userTypes();
  const [plusOpen, setPlusOpen] = useState(false);
  const [plusMode, setPlusMode] = useState<PlusMenuMode>("root");

  const closePlus = (): void => {
    setPlusOpen(false);
    setPlusMode("root");
  };

  const objectTypes = types.filter((view) => view.kind === "object");

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <span className="brand">nylium</span>
        <div className="sidebar-plus">
          <button
            className="icon-button"
            title="Create"
            onClick={() => (plusOpen ? closePlus() : setPlusOpen(true))}
          >
            +
          </button>
          {plusOpen && (
            <>
              <div className="type-picker-backdrop" onClick={closePlus} />
              <div className="type-menu">
                {plusMode === "object" ? (
                  <>
                    <div className="type-menu-search">
                      <button
                        className="icon-button"
                        title="Back"
                        onClick={() => setPlusMode("root")}
                      >
                        ←
                      </button>
                      <span className="dim type-menu-title">New object</span>
                    </div>
                    <div className="type-menu-list">
                      {objectTypes.map((view) => (
                        <button
                          key={view.name}
                          className="type-menu-row"
                          onClick={() => {
                            closePlus();
                            void props.workspace.createObject(view.name);
                          }}
                        >
                          <TypeIcon icon={view.icon} color={view.color} size={15} />
                          <span>{view.name}</span>
                        </button>
                      ))}
                      {objectTypes.length === 0 && (
                        <div className="type-menu-empty dim">No types yet</div>
                      )}
                    </div>
                  </>
                ) : (
                  <div className="type-menu-list">
                    <button
                      className="type-menu-row"
                      onClick={() => {
                        closePlus();
                        props.workspace.openCreateType();
                      }}
                    >
                      New type
                    </button>
                    <button
                      className="type-menu-row"
                      onClick={() => setPlusMode("object")}
                    >
                      New object
                    </button>
                    <button
                      className="type-menu-row"
                      onClick={() => {
                        closePlus();
                        props.workspace.openCreateEnum();
                      }}
                    >
                      New enum
                    </button>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
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
