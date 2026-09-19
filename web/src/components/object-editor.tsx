import type { ReactElement } from "react";
import { useMemo } from "react";
import type { FunctionView, ObjectView, PropValue, TypeView } from "../contracts";
import { PropValues, TypeNames, WireUrls } from "../contracts";
import { ObjectEditorStore } from "../state/object-editor";
import { useObservable } from "../state/use-observable";
import { useSaveShortcut } from "../state/use-save-shortcut";
import { usePinTabOnEdit } from "../state/use-pin-tab-on-edit";
import { WorkspaceStore } from "../state/workspace";
import { FieldEditor } from "./field-editors";
import { BacklinkChips } from "./backlink-chips";
import { TagChips } from "./tag-chips";
import { TypeIcon } from "./type-icon";
import { FloatingMenu } from "./floating-menu";
import { FieldModel } from "../fields/field-model";
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
      functions={state.functions}
      workspace={props.workspace}
    />
  );
}

function ObjectEditorInner(props: {
  object: ObjectView;
  schema: TypeView;
  functions: readonly FunctionView[];
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
    <div className="editor-shell object-editor">
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
          <a
            className="icon-button"
            href={WireUrls.objectExport(props.object.uuid)}
            title="Export .md"
          >
            <span className="material-symbols-outlined" style={{ fontSize: 20 }}>
              download
            </span>
          </a>
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
              {prop.functionUuid !== null && (
                <button
                  className="function-bind-trigger bound"
                  title="Unbind function"
                  onClick={() => void store.setPropFunction(prop.key, null)}
                >
                  <span className="function-bind-label">
                    <span className="tab-function-icon">ƒ</span>
                    <span className="function-bind-name">unbind</span>
                  </span>
                </button>
              )}
            </div>
          ))}
        </div>
      )}
      <FunctionBindSection
        object={props.object}
        schema={props.schema}
        functions={props.functions}
        onBind={(propKey, uuid) => void store.setPropFunction(propKey, uuid)}
      />
      <div className="object-editor-fields">
        {groupTraitFields(gridFields, props.schema).map((segment) => {
          if (segment.trait === null) {
            return segment.fields.map((field) => (
              <FieldEditor key={field.key} field={field} editor={store} />
            ));
          }
          // ADR-0013: props owned by a trait render as one group inside a
          // rounded frame in the trait's color — a visible capsule
          return (
            <div
              key={`trait-${segment.trait.name}`}
              className="trait-field-group"
              style={{ borderColor: segment.trait.color ?? undefined }}
            >
              <div
                className="trait-field-group-label"
                style={{ color: segment.trait.color ?? undefined }}
              >
                {segment.trait.name}
              </div>
              {segment.fields.map((field) => (
                <FieldEditor key={field.key} field={field} editor={store} />
              ))}
            </div>
          );
        })}
      </div>
      <BacklinkChips workspace={props.workspace} object={props.object} />
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

/** ADR-0029: instance-level function binding. Lists every bindable scalar
 * prop of this object and, for each, a menu of functions whose input type
 * is this object's type and whose output type equals the prop's value
 * type — the backend enforces the same match. Bound props carry an
 * "unbind" row instead. */
function FunctionBindSection(props: {
  object: ObjectView;
  schema: TypeView;
  functions: readonly FunctionView[];
  onBind: (propKey: string, functionUuid: string | null) => void;
}): ReactElement | null {
  const bindable = props.schema.props.filter(
    (prop) =>
      prop.key !== "name" &&
      prop.formula === null &&
      prop.collect === null &&
      prop.trait === null &&
      TypeNames.isScalar(prop.value_type),
  );
  if (bindable.length === 0) {
    return null;
  }
  return (
    <div className="object-editor-functions">
      <div className="computed-header dim">Functions</div>
      {bindable.map((prop) => {
        const boundUuid = props.object.function_bindings[prop.key] ?? null;
        const boundName =
          props.functions.find((fn) => fn.uuid === boundUuid)?.name ?? null;
        const candidates = props.functions.filter(
          (fn) =>
            fn.input_type === props.object.type_name &&
            fn.output_type === prop.value_type,
        );
        return (
          <div className="function-bind-row" key={prop.key}>
            <span className="function-bind-prop">{prop.key}</span>
            <FloatingMenu
              wrapperClassName="function-bind"
              triggerClassName={
                boundUuid !== null
                  ? "function-bind-trigger bound"
                  : "function-bind-trigger"
              }
              title={
                boundUuid !== null
                  ? `Bound to ${boundName ?? "function"}`
                  : "Bind function"
              }
              trigger={
                <span className="function-bind-label">
                  <span className="tab-function-icon">ƒ</span>
                  {boundName !== null && (
                    <span className="function-bind-name">{boundName}</span>
                  )}
                </span>
              }
            >
              {(close) => (
                <div className="type-menu-list">
                  {boundUuid !== null && (
                    <button
                      className="type-menu-row"
                      onClick={() => {
                        props.onBind(prop.key, null);
                        close();
                      }}
                    >
                      Unbind
                    </button>
                  )}
                  {candidates.length === 0 && (
                    <div className="type-menu-empty dim">
                      No function with a matching output.
                    </div>
                  )}
                  {candidates.map((fn) => (
                    <button
                      key={fn.uuid}
                      className="type-menu-row"
                      onClick={() => {
                        props.onBind(prop.key, fn.uuid);
                        close();
                      }}
                    >
                      <span className="tab-function-icon">ƒ</span>
                      <span>{fn.name}</span>
                    </button>
                  ))}
                </div>
              )}
            </FloatingMenu>
          </div>
        );
      })}
    </div>
  );
}

/** A run of editor fields that either all belong to one trait or to the
 * type itself (`trait: null`). Consecutive fields of the same trait stay
 * one segment so they render inside a single rounded frame. */
interface FieldSegment {
  readonly trait: { readonly name: string; readonly color: string | null } | null;
  readonly fields: FieldModel[];
}

function groupTraitFields(
  fields: readonly FieldModel[],
  schema: TypeView,
): FieldSegment[] {
  const segments: FieldSegment[] = [];
  for (const field of fields) {
    const traitProp = schema.props.find(
      (prop) => prop.key === field.key && prop.trait !== null,
    );
    const last = segments[segments.length - 1];
    if (traitProp !== undefined && last?.trait?.name === traitProp.trait) {
      last.fields.push(field);
      continue;
    }
    segments.push({
      trait:
        traitProp === undefined
          ? null
          : { name: traitProp.trait as string, color: traitProp.trait_color },
      fields: [field],
    });
  }
  return segments;
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
  const url = WireUrls.file(props.object.uuid);
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
