import type { ReactElement } from "react";
import type { TypeView } from "../contracts";
import { TypeNames } from "../contracts";

/** ADR-0025: pick the member key an Array<T> prop is collected by. A single
 * dropdown over the element type's props; the backend validates the member
 * is an ordered scalar on save. */
export function CollectSelector(props: {
  valueType: string;
  collect: string | null;
  onChange: (collect: string | null) => void;
  types: readonly TypeView[];
}): ReactElement {
  const { valueType, collect, onChange, types } = props;
  const element = TypeNames.isArray(valueType) ? TypeNames.elementOf(valueType) : null;
  const members =
    element !== null
      ? (types.find((t) => t.name === element)?.props.map((m) => m.key) ?? [])
      : [];
  return (
    <span className="collect-selector">
      <span className="collect-label">собирать по</span>
      <select
        className="block-select"
        value={collect ?? ""}
        onChange={(e) => onChange(e.target.value === "" ? null : e.target.value)}
      >
        <option value="">—</option>
        {members.map((member) => (
          <option key={member} value={member}>
            {member}
          </option>
        ))}
      </select>
    </span>
  );
}
