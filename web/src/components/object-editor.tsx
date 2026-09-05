import type { ReactElement } from "react";
import { useMemo } from "react";
import type { ObjectView, PropValue, TypeView } from "../contracts";
import { PropValues, TypeNames } from "../contracts";
import { NyliumApi } from "../net/nylium-api";
import { ObjectEditorStore } from "../state/object-editor";
import { useObservable } from "../state/use-observable";
import { useSaveShortcut } from "../state/use-save-shortcut";
import { usePinTabOnEdit } from "../state/use-pin-tab-on-edit";
import { WorkspaceStore } from "../state/workspace";
import { FieldEditor } from "./field-editors";
import { TagChips } from "./tag-chips";
import { TypeIcon } from "./type-icon";
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
  useSaveShortcut(() => void store.save(), editorState.dirty && !editorState.saving);
  usePinTabOnEdit(props.workspace, editorState.dirty);

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
        <div className="object-name-row">
          <TypeIcon icon={props.schema.icon} color={props.schema.color} size={24} />
          <input
            className="input object-name-input"
            placeholder="Name"
            value={titleField.draft}
            onChange={(event) => {
              titleField.draft = event.target.value;
              store.touch();
            }}
          />
        </div>
      )}
      <TagChips editor={store} />
      {TypeNames.isFileType(props.object.type_name) && (
        <FileBlock object={props.object} />
      )}
      {editorState.computed.length > 0 && (
        <div className="object-editor-computed">
          <div className="computed-header dim">Computed</div>
          {editorState.computed.map((prop) => (
            <div className="computed-row" key={prop.key}>
              <span className="computed-label">{prop.key}</span>
              <span className="computed-value">{computedText(prop.value)}</span>
              <span className="computed-badge dim">
                {prop.functionUuid !== null ? "function" : "formula"}
              </span>
            </div>
          ))}
        </div>
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

/** ADR-0005/0007: a computed prop is always scalar on read — render its
 * wire value, or an em-dash when unset. */
function computedText(value: PropValue | undefined): string {
  if (value === undefined) {
    return "—";
  }
  if (PropValues.isScalar(value) && value.value !== null) {
    return String(value.value);
  }
  return "—";
}

/** ADR-0006: file objects render their blob inline (images) or as a
 * download affordance (documents/files). The blob URL is uuid-keyed, so
 * renames never break it. */
function FileBlock(props: { object: ObjectView }): ReactElement {
  const url = NyliumApi.fileUrl(props.object.uuid);
  const name = props.object.props["name"];
  const label =
    name !== undefined && "value" in name && typeof name.value === "string"
      ? name.value
      : "file";
  if (props.object.type_name === TypeNames.IMAGE) {
    return (
      <div className="file-block">
        <img className="file-block-image" src={url} alt={label} />
        <a className="file-block-link dim" href={url} download={label}>
          Download original
        </a>
      </div>
    );
  }
  return (
    <div className="file-block">
      <a className="file-block-link" href={url} download={label}>
        Download {label}
      </a>
    </div>
  );
}
