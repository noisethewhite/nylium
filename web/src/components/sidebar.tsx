import type { ReactElement } from "react";
import { useState } from "react";
import { AuthStore } from "../state/auth";
import { useObservable } from "../state/use-observable";
import { WorkspaceStore } from "../state/workspace";
import { FloatingMenu } from "./floating-menu";
import { NameSearch } from "./name-search";
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
  const [plusMode, setPlusMode] = useState<PlusMenuMode>("root");
  const objectTypes = types.filter((view) => view.kind === "object");

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <span className="brand">nylium</span>
        <FloatingMenu
          wrapperClassName="sidebar-plus"
          triggerClassName="icon-button"
          menuClassName="type-menu"
          title="Create"
          trigger="+"
        >
          {(close) => {
            const dismiss = (): void => {
              setPlusMode("root");
              close();
            };
            if (plusMode === "object") {
              return (
                <NameSearch
                  items={objectTypes}
                  getKey={(view) => view.name}
                  getLabel={(view) => view.name}
                  renderIcon={(view) => (
                    <TypeIcon icon={view.icon} color={view.color} size={15} />
                  )}
                  placeholder="Search types…"
                  emptyLabel="No types yet"
                  header={
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
                  }
                  onPick={(view) => {
                    dismiss();
                    void props.workspace.createObject(view.name);
                  }}
                />
              );
            }
            return (
              <div className="type-menu-list">
                <button
                  className="type-menu-row"
                  onClick={() => {
                    dismiss();
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
                    dismiss();
                    props.workspace.openCreateEnum();
                  }}
                >
                  New enum
                </button>
              </div>
            );
          }}
        </FloatingMenu>
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
