import type { ReactElement } from "react";
import type { TypeView } from "../contracts";
import { WorkspaceStore } from "../state/workspace";

/** Content of a type tab: its schema and the create-object entry. */
export function TypeViewPanel(props: {
  workspace: WorkspaceStore;
  schema: TypeView;
}): ReactElement {
  return (
    <div className="tab-content">
      <header className="type-header">
        <h1>
          {props.schema.name}
          {props.schema.plural_name !== null && (
            <span className="dim type-plural">{props.schema.plural_name}</span>
          )}
        </h1>
        <button
          className="button button-primary"
          onClick={() => void props.workspace.createObject(props.schema.name)}
        >
          + New {props.schema.name}
        </button>
      </header>
      <div className="schema-props">
        {props.schema.props.length === 0 && (
          <p className="dim">No props in this type.</p>
        )}
        {props.schema.props.map((prop) => (
          <div className="schema-prop-row" key={prop.key}>
            <span>{prop.key}</span>
            <span className="dim">{prop.value_type}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
