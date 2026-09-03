import type { ReactElement } from "react";
import { useState } from "react";
import { TypeLabels, TypeNames } from "../contracts";
import { WorkspaceStore } from "../state/workspace";
import { FloatingMenu } from "./floating-menu";
import { NameSearch } from "./name-search";
import { TypeIcon } from "./type-icon";

/** Submenu the two bottom buttons open — same view, different wrapping. */
type ObjectMode = "single" | "array";

/** Scalars listed flat in the menu — the calendar family hides behind
 * its own submenu so five variants don't flood the list. */
const FLAT_SCALARS = [TypeNames.STRING, TypeNames.INTEGER, TypeNames.NUMERIC, TypeNames.BOOLEAN];

export function TypePicker(props: {
  workspace: WorkspaceStore;
  value: string;
  onChange: (value: string) => void;
}): ReactElement {
  const [objectMode, setObjectMode] = useState<ObjectMode | null>(null);
  const [calendarOpen, setCalendarOpen] = useState(false);

  const reset = (): void => {
    setObjectMode(null);
    setCalendarOpen(false);
  };

  const scalarIcon = (name: string): ReactElement => {
    const view = props.workspace.typeView(name);
    // builtins render gray by rule — their stored color IS gray, but
    // force it here so a stale backend value can't sneak color in
    return <TypeIcon icon={view?.icon ?? "inventory_2"} color="gray" size={15} />;
  };

  return (
    <FloatingMenu
      wrapperClassName="type-picker floating-menu-grow"
      triggerClassName="input type-picker-trigger"
      menuClassName="type-menu"
      trigger={
        <>
          <span className="material-symbols-outlined type-picker-chevron" aria-hidden>
            keyboard_arrow_down
          </span>
          {scalarIcon(props.value)}
          <span className="type-picker-value">{props.value}</span>
        </>
      }
    >
      {(close) => {
        const pick = (value: string): void => {
          props.onChange(value);
          reset();
          close();
        };
        if (objectMode !== null) {
          return (
            <NameSearch
              items={props.workspace.userTypes()}
              getKey={(view) => view.name}
              getLabel={(view) =>
                objectMode === "array" ? TypeNames.arrayOf(view.name) : view.name
              }
              renderIcon={(view) => (
                <TypeIcon icon={view.icon} color={view.color} size={15} />
              )}
              placeholder="Search types…"
              emptyLabel="No types"
              header={
                <div className="type-menu-search">
                  <button
                    className="icon-button"
                    title="Back"
                    onClick={() => setObjectMode(null)}
                  >
                    ←
                  </button>
                  <span className="dim type-menu-title">
                    {objectMode === "array" ? "Array of objects" : "Object"}
                  </span>
                </div>
              }
              onPick={(view) =>
                pick(
                  objectMode === "array" ? TypeNames.arrayOf(view.name) : view.name,
                )
              }
            />
          );
        }
        if (calendarOpen) {
          return (
            <>
              <div className="type-menu-search">
                <button
                  className="icon-button"
                  title="Back"
                  onClick={() => setCalendarOpen(false)}
                >
                  ←
                </button>
                <span className="dim type-menu-title">Date &amp; time</span>
              </div>
              <div className="type-menu-list">
                {TypeNames.CALENDAR.map((name) => (
                  <button key={name} className="type-menu-row" onClick={() => pick(name)}>
                    {scalarIcon(name)}
                    <span>{TypeLabels[name] ?? name}</span>
                  </button>
                ))}
              </div>
            </>
          );
        }
        return (
          <>
            <div className="type-menu-list">
              {FLAT_SCALARS.map((scalar) => (
                <button
                  key={scalar}
                  className="type-menu-row"
                  onClick={() => pick(scalar)}
                >
                  {scalarIcon(scalar)}
                  <span>{scalar}</span>
                </button>
              ))}
              <button className="type-menu-row" onClick={() => setCalendarOpen(true)}>
                {scalarIcon(TypeNames.DATE)}
                <span>Date &amp; time →</span>
              </button>
            </div>
            <div className="type-menu-divider" />
            <div className="type-menu-footer">
              <button className="type-menu-row" onClick={() => setObjectMode("single")}>
                Object
              </button>
              <button className="type-menu-row" onClick={() => setObjectMode("array")}>
                Array of objects
              </button>
            </div>
          </>
        );
      }}
    </FloatingMenu>
  );
}
