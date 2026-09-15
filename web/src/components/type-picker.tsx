import type { ReactElement } from "react";
import { useState } from "react";
import { TypeLabels, TypeNames } from "../contracts";
import { useObservable } from "../state/use-observable";
import { WorkspaceStore } from "../state/workspace";
import { FloatingMenu } from "./floating-menu";
import { NameSearch } from "./name-search";
import { TypeIcon } from "./type-icon";
import { TypeName } from "./type-name";

/** Submenu the two bottom buttons open — same view, different wrapping. */
type ObjectMode = "single" | "array";

/** Which submenu is on screen. One tagged state — mutually exclusive by
 * construction, instead of four booleans that can disagree. */
type Submenu =
  | { kind: "root" }
  | { kind: "object"; mode: ObjectMode }
  | { kind: "calendar" }
  | { kind: "unit" }
  | { kind: "any" };

/** Scalars listed flat in the menu — the calendar family hides behind
 * its own submenu so five variants don't flood the list. */
const FLAT_SCALARS = [TypeNames.STRING, TypeNames.INTEGER, TypeNames.NUMERIC, TypeNames.BOOLEAN];

export function TypePicker(props: {
  workspace: WorkspaceStore;
  value: string;
  onChange: (value: string) => void;
}): ReactElement {
  const [submenu, setSubmenu] = useState<Submenu>({ kind: "root" });
  const state = useObservable(props.workspace);

  const reset = (): void => setSubmenu({ kind: "root" });

  const scalarIcon = (name: string): ReactElement => {
    const view = props.workspace.typeView(name);
    // builtins render gray by rule — their stored color IS gray, but
    // force it here so a stale backend value can't sneak color in
    return <TypeIcon icon={view?.icon ?? "inventory_2"} color="gray" size={15} />;
  };

  /** Icon for the trigger: parameterized names (Numeric<Unit>) borrow
   * the parameter type's icon, everything else its own. */
  const triggerIcon = (): ReactElement => {
    const param = TypeNames.unitParamOf(props.value);
    if (param !== null) {
      const unit = props.workspace.typeView(param);
      return (
        <TypeIcon icon={unit?.icon ?? "straighten"} color={unit?.color ?? "gray"} size={15} />
      );
    }
    // ADR-0013: Any<Trait> renders the trait's color dot
    const bound = TypeNames.anyTraitOf(props.value);
    if (bound !== null) {
      const trait = state.traits.find((view) => view.name === bound);
      return (
        <span
          className="trait-dot"
          style={{ background: trait?.color ?? "var(--fg-dim)" }}
        />
      );
    }
    return scalarIcon(props.value);
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
          {triggerIcon()}
          <span className="type-picker-value">
            <TypeName workspace={props.workspace} name={props.value} />
          </span>
        </>
      }
    >
      {(close) => {
        const pick = (value: string): void => {
          props.onChange(value);
          reset();
          close();
        };
        if (submenu.kind === "object") {
          // ADR-0021: Array<Embedded> is allowed — ref and embedded types
          // are both valid array elements now
          const candidates = props.workspace.userTypes();
          return (
            <NameSearch
              items={candidates}
              getKey={(view) => view.name}
              getLabel={(view) =>
                submenu.mode === "array" ? TypeNames.arrayOf(view.name) : view.name
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
                    onClick={reset}
                  >
                    ←
                  </button>
                  <span className="dim type-menu-title">
                    {submenu.mode === "array" ? "Array of objects" : "Object"}
                  </span>
                </div>
              }
              onPick={(view) =>
                pick(
                  submenu.mode === "array" ? TypeNames.arrayOf(view.name) : view.name,
                )
              }
            />
          );
        }
        if (submenu.kind === "unit") {
          const units = props.workspace
            .userTypes()
            .filter((view) => view.kind === "unit");
          return (
            <NameSearch
              items={units}
              getKey={(view) => view.name}
              getLabel={(view) => TypeNames.unitNumericName(view.name)}
              renderIcon={(view) => (
                <TypeIcon icon={view.icon} color={view.color} size={15} />
              )}
              placeholder="Search units…"
              emptyLabel="No units yet"
              header={
                <div className="type-menu-search">
                  <button
                    className="icon-button"
                    title="Back"
                    onClick={reset}
                  >
                    ←
                  </button>
                  <span className="dim type-menu-title">Numeric with unit</span>
                </div>
              }
              onPick={(view) => pick(TypeNames.unitNumericName(view.name))}
            />
          );
        }
        if (submenu.kind === "calendar") {
          return (
            <>
              <div className="type-menu-search">
                <button
                  className="icon-button"
                  title="Back"
                  onClick={reset}
                >
                  ←
                </button>
                <span className="dim type-menu-title">Date &amp; time</span>
              </div>
              <div className="type-menu-list">
                {TypeNames.CALENDAR.map((name) => (
                  <button key={name} className="type-menu-row" onClick={() => pick(name)}>
                    {scalarIcon(name)}
                    <TypeName workspace={props.workspace} name={name} label={TypeLabels[name] ?? name} />
                  </button>
                ))}
              </div>
            </>
          );
        }
        if (submenu.kind === "any") {
          // ADR-0013: pick a trait to bind a polymorphic ref to
          return (
            <NameSearch
              items={state.traits}
              getKey={(view) => view.name}
              getLabel={(view) => TypeNames.anyWithTrait(view.name)}
              renderIcon={(view) => (
                <span className="trait-dot" style={{ background: view.color }} />
              )}
              placeholder="Search traits…"
              emptyLabel="No traits yet"
              header={
                <div className="type-menu-search">
                  <button
                    className="icon-button"
                    title="Back"
                    onClick={reset}
                  >
                    ←
                  </button>
                  <span className="dim type-menu-title">Any with trait</span>
                </div>
              }
              onPick={(view) => pick(TypeNames.anyWithTrait(view.name))}
            />
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
                  <TypeName workspace={props.workspace} name={scalar} />
                </button>
              ))}
              <button className="type-menu-row" onClick={() => setSubmenu({ kind: "calendar" })}>
                {scalarIcon(TypeNames.DATE)}
                <span>Date &amp; time →</span>
              </button>
              <button className="type-menu-row" onClick={() => setSubmenu({ kind: "unit" })}>
                {scalarIcon(TypeNames.NUMERIC)}
                <span>Numeric with unit →</span>
              </button>
              <button
                className="type-menu-row"
                title="Link to any object carrying a trait (ADR-0013)"
                onClick={() => setSubmenu({ kind: "any" })}
              >
                <span className="trait-dot trait-dot-hollow" />
                <span>Any with trait →</span>
              </button>
            </div>
            <div className="type-menu-divider" />
            <div className="type-menu-list">
              {TypeNames.FILES.map((name) => (
                <button
                  key={name}
                  className="type-menu-row"
                  onClick={() => pick(name)}
                >
                  {scalarIcon(name)}
                  <TypeName workspace={props.workspace} name={name} />
                </button>
              ))}
            </div>
            <div className="type-menu-divider" />
            <div className="type-menu-footer">
              <button className="type-menu-row" onClick={() => setSubmenu({ kind: "object", mode: "single" })}>
                Object
              </button>
              <button className="type-menu-row" onClick={() => setSubmenu({ kind: "object", mode: "array" })}>
                Array of objects
              </button>
            </div>
          </>
        );
      }}
    </FloatingMenu>
  );
}
