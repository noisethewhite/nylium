import type { ReactElement } from "react";
import { useMemo } from "react";
import type { ObjectView, TypeView } from "../contracts";
import { ObjectEditorStore } from "../state/object-editor";
import { useObservable } from "../state/use-observable";
import { WorkspaceStore } from "../state/workspace";
import { FieldEditor } from "./field-editors";
import { TextFieldModel } from "../fields/scalar-fields";

export function ObjectEditor(props: {
  workspace: WorkspaceStore;
  object: ObjectView;
}): ReactElement {
  const state = useObservable(props.workspace);
  const schema =
    state.types.find((view) => view.name === props.object.type_name) ?? null;

  if (schema === null) {
    return <div className="empty-state dim">Type is gone.</div>;
  }
  // key remounts the inner editor per object — drafts never leak
  // between objects
  return (
    <ObjectEditorInner
      key={props.object.uuid}
      object={props.object}
      schema={schema}
      workspace={props.workspace}
    />
  );
}

function ObjectEditorInner(props: {
  object: ObjectView;
  schema: TypeView;
  workspace: WorkspaceStore;
}): ReactElement {
  const store = useMemo(
    () => ObjectEditorStore.create(props.object, props.schema, props.workspace),
    [props.object, props.schema, props.workspace],
  );
  const editorState = useObservable(store);

  const fields = editorState.fields;
  const first = fields[0];
  // the schema's first prop is the pinned `name` text prop — it renders
  // as the editable page heading instead of a grid row
  const titleField =
    first instanceof TextFieldModel && first.key === "name" ? first : undefined;
  const gridFields = titleField !== undefined ? fields.slice(1) : fields;

  return (
    <div className="object-editor">
      {titleField !== undefined && (
        <input
          className="input object-name-input"
          placeholder="Name"
          value={titleField.draft}
          onChange={(event) => {
            titleField.draft = event.target.value;
            store.touch();
          }}
        />
      )}
      <div className="object-editor-fields">
        {gridFields.map((field) => (
          <FieldEditor key={field.key} field={field} editor={store} />
        ))}
      </div>
      {editorState.error !== null && (
        <div className="error-banner">{editorState.error}</div>
      )}
      <div className="object-editor-actions">
        <button
          className="button button-primary"
          disabled={!editorState.dirty || editorState.saving}
          onClick={() => void store.save()}
        >
          {editorState.saving ? "Saving…" : "Save"}
        </button>
        <button
          className="button button-danger"
          onClick={() => void store.deleteObject()}
        >
          Delete
        </button>
      </div>
    </div>
  );
}
