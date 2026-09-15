import type { ReactElement } from "react";
import type { TypeView } from "../contracts";
import { TypeLabels } from "../contracts";
import { Lock } from "./file-type-view";
import { TypeIcon } from "./type-icon";

/** Read-only panel for a built-in scalar type (String, Numeric, Date, …).
 * Scalars are immutable — no editor, no rename, no delete — so this just
 * names the type and marks it locked. */
export function ScalarTypePanel(props: { schema: TypeView }): ReactElement {
  const { schema } = props;
  const label = TypeLabels[schema.name] ?? schema.name;
  return (
    <div className="editor-shell">
      <div className="editor-header">
        <span className="dim editor-header-title">
          <Lock /> Built-in scalar type
        </span>
      </div>
      <div className="editor-boxes">
        <div className="editor-box">
          <span className="editor-box-label">Type name</span>
          <div className="editor-box-content">
            <TypeIcon icon={schema.icon} color={schema.color} size={22} variant="scalar" />
            <span className="type-name-input scalar-name">{schema.name}</span>
          </div>
        </div>
      </div>
      <p className="dim type-file-note">
        {schema.name}
        {label !== schema.name ? ` (“${label}”)` : ""} is a built-in scalar type.
        It is read-only — scalars cannot be renamed, edited, or deleted.
      </p>
    </div>
  );
}
