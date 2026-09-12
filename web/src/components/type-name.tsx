import type { ReactElement } from "react";
import { TypeNames } from "../contracts";
import { useObservable } from "../state/use-observable";
import { WorkspaceStore } from "../state/workspace";

/** A type name rendered with its icon's color — bold always, monospace
 * when it names a scalar. Color resolution mirrors the type picker's
 * `triggerIcon()`: parameterized names borrow their parameter's color,
 * `Any<Trait>` borrows the trait's color, everything else its own. */
export function TypeName(props: {
  workspace: WorkspaceStore;
  name: string;
  /** display text override (calendar family shows human labels) — color
   * and scalar styling still resolve from `name` */
  label?: string;
}): ReactElement {
  const { workspace, name } = props;
  const state = useObservable(workspace);

  const color = (): string => {
    const param = TypeNames.unitParamOf(name);
    if (param !== null) {
      return workspace.typeView(param)?.color ?? "var(--fg-dim)";
    }
    const bound = TypeNames.anyTraitOf(name);
    if (bound !== null) {
      const trait = state.traits.find((view) => view.name === bound);
      return trait?.color ?? "var(--fg-dim)";
    }
    return workspace.typeView(name)?.color ?? "var(--fg-dim)";
  };

  const isScalar = TypeNames.isScalar(name);
  const className = `type-name-text${isScalar ? " type-name-scalar" : ""}`;

  return (
    <span className={className} style={{ color: color() }}>
      {props.label ?? name}
    </span>
  );
}
