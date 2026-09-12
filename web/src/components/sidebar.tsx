import type { ReactElement } from "react";
import { useRef, useState } from "react";
import { TypeNames } from "../contracts";
import { AuthStore } from "../state/auth";
import { useObservable } from "../state/use-observable";
import { WorkspaceStore } from "../state/workspace";
import { FloatingMenu } from "./floating-menu";
import { NameSearch } from "./name-search";
import { ObjectLabels } from "./object-labels";
import { StorageMenu } from "./storage-menu";
import { TypeIcon } from "./type-icon";

/** What the "+" popover is showing: the root menu or the pick-a-type
 * list that "New object" expands into. */
type PlusMenuMode = "root" | "object" | "file";

/** Temporary explorer: every type and every object, flat. */
export function Sidebar(props: {
  workspace: WorkspaceStore;
  auth: AuthStore;
  /** Fired when the user picks a destination; the mobile drawer host
   * uses it to close itself. Inert on desktop. */
  onNavigate: () => void;
}): ReactElement {
  const state = useObservable(props.workspace);
  const authState = useObservable(props.auth);
  const types = props.workspace.userTypes();
  const [plusMode, setPlusMode] = useState<PlusMenuMode>("root");
  const uploadType = useRef<string | null>(null);
  const fileInput = useRef<HTMLInputElement | null>(null);
  const objectTypes = types.filter(
    (view) => view.kind === "object" && !view.embedded,
  );
  const fileTypes = state.types.filter((view) => TypeNames.isFileType(view.name));
  const scalarTypes = state.types.filter((view) => TypeNames.isScalar(view.name));

  return (
    <aside
      className="sidebar"
      onClickCapture={(event) => {
        // Any tap on a nav row is a navigation: tell the host so the
        // mobile drawer can close. Capture phase so row-level handlers
        // cannot swallow it.
        const target = event.target;
        if (
          target instanceof Element &&
          target.closest("nav.sidebar-scroll button") !== null
        ) {
          props.onNavigate();
        }
      }}
    >
      <input
        ref={fileInput}
        type="file"
        hidden
        onChange={(event) => {
          const file = event.target.files?.[0];
          event.target.value = "";
          if (file !== undefined && uploadType.current !== null) {
            void props.workspace.uploadFile(uploadType.current, file);
          }
        }}
      />
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
            if (plusMode === "file") {
              return (
                <NameSearch
                  items={fileTypes}
                  getKey={(view) => view.name}
                  getLabel={(view) => view.name}
                  renderIcon={(view) => (
                    <TypeIcon icon={view.icon} color={view.color} size={15} />
                  )}
                  placeholder="Search file types…"
                  emptyLabel="No file types"
                  header={
                    <div className="type-menu-search">
                      <button
                        className="icon-button"
                        title="Back"
                        onClick={() => setPlusMode("root")}
                      >
                        ←
                      </button>
                      <span className="dim type-menu-title">New file</span>
                    </div>
                  }
                  onPick={(view) => {
                    dismiss();
                    uploadType.current = view.name;
                    fileInput.current?.click();
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
                  onClick={() => {
                    dismiss();
                    props.workspace.openCreateTrait();
                  }}
                >
                  New trait
                </button>
                <button
                  className="type-menu-row"
                  onClick={() => setPlusMode("object")}
                >
                  New object
                </button>
                <button
                  className="type-menu-row"
                  onClick={() => setPlusMode("file")}
                >
                  New file
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
                <button
                  className="type-menu-row"
                  onClick={() => {
                    dismiss();
                    props.workspace.openCreateUnit();
                  }}
                >
                  New unit
                </button>
                <button
                  className="type-menu-row"
                  onClick={() => {
                    dismiss();
                    props.workspace.openCreateFunction();
                  }}
                >
                  New function
                </button>
              </div>
            );
          }}
        </FloatingMenu>
      </div>
      <nav className="sidebar-scroll">
        <div className="type-row" key="calendar">
          <button
            className="type-row-name"
            onClick={() => props.workspace.openCalendar()}
          >
            <span
              className="material-symbols-outlined"
              style={{ fontSize: 15, color: "var(--fg-dim)" }}
            >
              calendar_month
            </span>
            <span>Calendar</span>
          </button>
        </div>
        <div className="sidebar-section">Types</div>
        {types.map((view) => (
          <div className="type-row" key={view.name}>
            <button
              className="type-row-name"
              onClick={() => props.workspace.openType(view.name)}
            >
              <TypeIcon icon={view.icon} color={view.color} />
              <span>{view.name}</span>
              {view.embedded && <span className="embedded-badge">embedded</span>}
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
        <div className="sidebar-section">Files</div>
        {fileTypes.map((view) => (
          <div className="type-row" key={view.name}>
            <button
              className="type-row-name"
              onClick={() => props.workspace.openType(view.name)}
            >
              <TypeIcon icon={view.icon} color={view.color} />
              <span>{view.name}</span>
            </button>
          </div>
        ))}
        <div className="sidebar-section">Traits</div>
        {state.traits.map((trait) => (
          <div className="type-row" key={trait.name}>
            <button
              className="type-row-name"
              onClick={() => props.workspace.openTrait(trait.name)}
            >
              <span className="trait-dot" style={{ background: trait.color }} />
              <span>{trait.name}</span>
            </button>
            <button
              className="icon-button type-row-delete"
              title={`Delete trait ${trait.name}`}
              onClick={() => void props.workspace.deleteTrait(trait.name)}
            >
              ×
            </button>
          </div>
        ))}
        <div className="sidebar-section">Scalars</div>
        {scalarTypes.map((view) => (
          <div className="type-row" key={view.name}>
            <button
              className="type-row-name"
              onClick={() => props.workspace.openType(view.name)}
            >
              <TypeIcon icon={view.icon} color={view.color} variant="scalar" />
              <span className="scalar-name">{view.name}</span>
            </button>
          </div>
        ))}
        <div className="sidebar-section">Functions</div>
        {state.functions.map((fn) => (
          <div className="type-row" key={fn.uuid}>
            <button
              className="type-row-name"
              onClick={() => props.workspace.openFunction(fn.uuid)}
            >
              <span className="tab-function-icon">ƒ</span>
              <span>{fn.name}</span>
            </button>
            <button
              className="icon-button type-row-delete"
              title={`Delete function ${fn.name}`}
              onClick={() => void props.workspace.deleteFunction(fn.uuid)}
            >
              ×
            </button>
          </div>
        ))}
        <div className="sidebar-section">Objects</div>
        {state.objects.map((view) => {
          const type = state.types.find((entry) => entry.name === view.type_name);
          return (
            <button
              className="type-row object-entry"
              key={view.uuid}
              title={view.uuid}
              onClick={() => props.workspace.openObject(view.uuid)}
            >
              {type !== undefined && <TypeIcon icon={type.icon} color={type.color} />}
              <span className="type-row-name">{ObjectLabels.of(view)}</span>
              <span className="dim">{view.type_name}</span>
            </button>
          );
        })}
      </nav>
      <div className="sidebar-footer">
        <span className="sidebar-user">{authState.userName}</span>
        <StorageMenu workspace={props.workspace} />
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
