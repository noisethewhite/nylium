import type { ReactElement } from "react";
import { useMemo } from "react";
import type { ObjectView, TypeView } from "../contracts";
import { ObjectEditorStore } from "../state/object-editor";
import { useObservable } from "../state/use-observable";
import { WorkspaceStore } from "../state/workspace";
import { FieldEditor } from "./field-editors";

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

  return (
    <div className="object-editor">
      <div className="object-editor-fields">
        {editorState.fields.map((field) => (
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
