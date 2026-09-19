import type { ReactElement, ReactNode } from "react";
import { Fragment, useMemo, useRef, useState } from "react";
import { TypeLevels, TypeNames } from "../contracts";
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

/** One explorer row: icon + label opens the page, optional trailing
 * delete. All five sections below render through this so the markup
 * lives in exactly one place. */
function SidebarRow(props: {
  icon: ReactNode;
  label: ReactNode;
  onOpen: () => void;
  deleteTitle?: string;
  onDelete?: () => void;
}): ReactElement {
  return (
    <div className="type-row">
      <button className="type-row-name" onClick={props.onOpen}>
        {props.icon}
        {props.label}
      </button>
      {props.onDelete !== undefined && (
        <button
          className="icon-button type-row-delete"
          title={props.deleteTitle}
          onClick={props.onDelete}
        >
          ×
        </button>
      )}
    </div>
  );
}

/** A collapsible explorer section: a header toggles a search box and a
 * scrollable list of rows. Generic over the item type so every section
 * (Types, Objects, Traits, …) shares one markup and one search path. */
function SidebarSection<T>(props: {
  title: string;
  items: readonly T[];
  getKey: (item: T) => string;
  getLabel: (item: T) => string;
  render: (item: T) => ReactNode;
}): ReactElement {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const needle = query.trim().toLowerCase();
  const matches = props.items.filter((item) =>
    props.getLabel(item).toLowerCase().includes(needle),
  );
  return (
    <div className="sidebar-section">
      <button
        className="sidebar-section-header"
        onClick={() => setOpen((value) => !value)}
      >
        <span className="sidebar-section-title">{props.title}</span>
        <span className="sidebar-section-count">{props.items.length}</span>
        <span
          className={`material-symbols-outlined sidebar-section-caret${open ? " open" : ""}`}
          style={{ fontSize: 15, color: "var(--fg-dim)" }}
        >
          expand_more
        </span>
      </button>
      {open && (
        <div className="sidebar-section-body">
          <input
            className="input sidebar-section-search"
            placeholder={`Search ${props.title.toLowerCase()}…`}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <div className="sidebar-section-list">
            {matches.map((item) => (
              <Fragment key={props.getKey(item)}>{props.render(item)}</Fragment>
            ))}
            {matches.length === 0 && (
              <div className="sidebar-section-empty dim">No matches</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

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
  // Reference-chain depth per object type — orders Types and Objects by
  // how deep each type's link chain runs (a type linking to level-N is
  // N+1). Non-object kinds and unresolved names fall back to level 1.
  const levels = useMemo(() => TypeLevels.compute(state.types), [state.types]);
  const levelOf = (name: string): number => levels.get(name) ?? 1;
  const byLevel = <T,>(
    entries: readonly T[],
    key: (entry: T) => string,
  ): readonly T[] =>
    [...entries].sort((a, b) => {
      const la = levelOf(key(a));
      const lb = levelOf(key(b));
      return la !== lb ? la - lb : key(a).localeCompare(key(b));
    });

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
                      <span className="dim type-menu-title">New Object</span>
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
                      <span className="dim type-menu-title">New File</span>
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
                  <span
                    className="material-symbols-outlined"
                    style={{ fontSize: 15, color: "var(--fg-dim)" }}
                  >
                    inventory_2
                  </span>
                  New Type
                </button>
                <button
                  className="type-menu-row"
                  onClick={() => {
                    dismiss();
                    props.workspace.openCreateTrait();
                  }}
                >
                  <span
                    className="material-symbols-outlined"
                    style={{ fontSize: 15, color: "var(--fg-dim)" }}
                  >
                    tag
                  </span>
                  New Trait
                </button>
                <button
                  className="type-menu-row"
                  onClick={() => setPlusMode("object")}
                >
                  <span
                    className="material-symbols-outlined"
                    style={{ fontSize: 15, color: "var(--fg-dim)" }}
                  >
                    note
                  </span>
                  New Object
                </button>
                <button
                  className="type-menu-row"
                  onClick={() => setPlusMode("file")}
                >
                  <span
                    className="material-symbols-outlined"
                    style={{ fontSize: 15, color: "var(--fg-dim)" }}
                  >
                    description
                  </span>
                  New File
                </button>
                <button
                  className="type-menu-row"
                  onClick={() => {
                    dismiss();
                    props.workspace.openCreateEnum();
                  }}
                >
                  <span
                    className="material-symbols-outlined"
                    style={{ fontSize: 15, color: "var(--fg-dim)" }}
                  >
                    lists
                  </span>
                  New Enum
                </button>
                <button
                  className="type-menu-row"
                  onClick={() => {
                    dismiss();
                    props.workspace.openCreateUnit();
                  }}
                >
                  <span
                    className="material-symbols-outlined"
                    style={{ fontSize: 15, color: "var(--fg-dim)" }}
                  >
                    straighten
                  </span>
                  New Unit
                </button>
                <button
                  className="type-menu-row"
                  onClick={() => {
                    dismiss();
                    props.workspace.openCreateFunction();
                  }}
                >
                  <span
                    className="material-symbols-outlined"
                    style={{ fontSize: 15, color: "var(--fg-dim)" }}
                  >
                    functions
                  </span>
                  New Function
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
        <SidebarSection
          title="Types"
          items={byLevel(types, (view) => view.name)}
          getKey={(view) => view.name}
          getLabel={(view) => view.name}
          render={(view) => (
            <SidebarRow
              icon={<TypeIcon icon={view.icon} color={view.color} />}
              label={
                <>
                  <span className="type-name-text" style={{ color: view.color }}>{view.name}</span>
                  {view.embedded && <span className="embedded-badge">embedded</span>}
                  <span className="type-level dim">L{levelOf(view.name)}</span>
                </>
              }
              onOpen={() => props.workspace.openType(view.name)}
              deleteTitle={`Delete type ${view.name}`}
              onDelete={() => void props.workspace.deleteType(view.name)}
            />
          )}
        />
        <SidebarSection
          title="Files"
          items={fileTypes}
          getKey={(view) => view.name}
          getLabel={(view) => view.name}
          render={(view) => (
            <SidebarRow
              icon={<TypeIcon icon={view.icon} color={view.color} />}
              label={
                <span className="type-name-text" style={{ color: view.color }}>{view.name}</span>
              }
              onOpen={() => props.workspace.openType(view.name)}
            />
          )}
        />
        <SidebarSection
          title="Traits"
          items={state.traits}
          getKey={(trait) => trait.name}
          getLabel={(trait) => trait.name}
          render={(trait) => (
            <SidebarRow
              icon={<span className="trait-dot" style={{ background: trait.color }} />}
              label={<span>{trait.name}</span>}
              onOpen={() => props.workspace.openTrait(trait.name)}
              deleteTitle={`Delete trait ${trait.name}`}
              onDelete={() => void props.workspace.deleteTrait(trait.name)}
            />
          )}
        />
        <SidebarSection
          title="Scalars"
          items={scalarTypes}
          getKey={(view) => view.name}
          getLabel={(view) => view.name}
          render={(view) => (
            <SidebarRow
              icon={<TypeIcon icon={view.icon} color={view.color} variant="scalar" />}
              label={<span className="scalar-name">{view.name}</span>}
              onOpen={() => props.workspace.openType(view.name)}
            />
          )}
        />
        <SidebarSection
          title="Functions"
          items={state.functions}
          getKey={(fn) => fn.uuid}
          getLabel={(fn) => fn.name}
          render={(fn) => (
            <SidebarRow
              icon={<span className="tab-function-icon">ƒ</span>}
              label={<span>{fn.name}</span>}
              onOpen={() => props.workspace.openFunction(fn.uuid)}
              deleteTitle={`Delete function ${fn.name}`}
              onDelete={() => void props.workspace.deleteFunction(fn.uuid)}
            />
          )}
        />
        <SidebarSection
          title="Objects"
          items={byLevel(state.objects, (view) => view.type_name)}
          getKey={(view) => view.uuid}
          getLabel={(view) => ObjectLabels.of(view)}
          render={(view) => {
            const type = state.types.find((entry) => entry.name === view.type_name);
            return (
              <button
                className="type-row object-entry"
                title={view.uuid}
                onClick={() => props.workspace.openObject(view.uuid)}
              >
                {type !== undefined && <TypeIcon icon={type.icon} color={type.color} />}
                <span className="type-row-name">{ObjectLabels.of(view)}</span>
                <span className="dim">{view.type_name}</span>
              </button>
            );
          }}
        />
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
