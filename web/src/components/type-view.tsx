import type { DragEvent, ReactElement } from "react";
import { useEffect, useState } from "react";
import type { FunctionView, TypeView } from "../contracts";
import { TypeNames } from "../contracts";
import { useObservable } from "../state/use-observable";
import { useSaveShortcut } from "../state/use-save-shortcut";
import { usePinTabOnEdit } from "../state/use-pin-tab-on-edit";
import { WorkspaceStore } from "../state/workspace";
import { FloatingMenu } from "./floating-menu";
import { IconPicker } from "./icon-picker";
import { TypePicker } from "./type-picker";

/** One row of the editor's draft — uuid null marks a not-yet-created
 * prop; everything else is matched to the live schema by uuid. */
interface PropDraft {
  readonly uuid: string | null;
  readonly key: string;
  readonly valueType: string;
}

function draftsOf(schema: TypeView): PropDraft[] {
  // ADR-0013: trait-owned props are not editable here — they belong to
  // the trait and render read-only below; the draft is own props only
  return schema.props
    .filter((prop) => prop.trait === null)
    .map((prop) => ({
      uuid: prop.uuid,
      key: prop.key,
      valueType: prop.value_type,
    }));
}

/** Six-dot grip (2×3) — the affordance that a schema row is draggable. */
function PropGrip(): ReactElement {
  const dots: ReactElement[] = [];
  for (let row = 0; row < 3; row += 1) {
    for (let col = 0; col < 2; col += 1) {
      dots.push(<circle key={`${row}-${col}`} cx={3 + col * 5} cy={3 + row * 4} r={1.4} />);
    }
  }
  return (
    <svg className="prop-grip-icon" width="11" height="14" viewBox="0 0 11 14">
      {dots}
    </svg>
  );
}

/** The type page IS the editor — same shape as the object editor:
 * borderless heading (the type name), prop rows with grips, one Save. */
export function TypeViewPanel(props: {
  workspace: WorkspaceStore;
  schema: TypeView;
}): ReactElement {
  const { workspace, schema } = props;
  const state = useObservable(workspace);
  const [nameDraft, setNameDraft] = useState(schema.name);
  const [pluralDraft, setPluralDraft] = useState(schema.plural_name ?? "");
  const [iconDraft, setIconDraft] = useState(schema.icon);
  const [colorDraft, setColorDraft] = useState(schema.color);
  const [rows, setRows] = useState<PropDraft[]>(() => draftsOf(schema));
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [overIndex, setOverIndex] = useState<number | null>(null);

  useEffect(() => {
    setNameDraft(schema.name);
    setPluralDraft(schema.plural_name ?? "");
    setIconDraft(schema.icon);
    setColorDraft(schema.color);
    setRows(draftsOf(schema));
  }, [schema]);

  const updateRow = (index: number, patch: Partial<PropDraft>): void => {
    setRows((drafts) =>
      drafts.map((draft, position) =>
        position === index ? { ...draft, ...patch } : draft,
      ),
    );
  };

  const dropAt = (target: number): void => {
    if (dragIndex === null || dragIndex === target) {
      return;
    }
    // the pinned `name` row never leaves position 0
    if (dragIndex === 0 || target === 0) {
      return;
    }
    setRows((drafts) => {
      const moved = drafts[dragIndex];
      if (moved === undefined) {
        return drafts;
      }
      const next = drafts.filter((_, position) => position !== dragIndex);
      next.splice(target, 0, moved);
      return next;
    });
    setDragIndex(null);
    setOverIndex(null);
  };

  const onDrop = (event: DragEvent, target: number): void => {
    event.preventDefault();
    dropAt(target);
  };

  const rowClass = (index: number): string => {
    const classes = ["prop-draft-row", "schema-prop-row"];
    if (index === dragIndex) {
      classes.push("schema-prop-row-dragging");
    }
    if (index === overIndex && dragIndex !== null && dragIndex !== index) {
      classes.push("schema-prop-row-over");
    }
    return classes.join(" ");
  };

  const pristine =
    nameDraft === schema.name &&
    pluralDraft === (schema.plural_name ?? "") &&
    iconDraft === schema.icon &&
    colorDraft === schema.color &&
    JSON.stringify(rows) === JSON.stringify(draftsOf(schema));
  const keys = rows.map((row) => row.key);
  const invalid =
    keys.some((key) => key.trim() === "") ||
    new Set(keys).size !== keys.length ||
    nameDraft.trim() === "";

  const save = (): void => {
    void workspace.saveTypeEdits(
      schema.name,
      { name: nameDraft.trim(), plural_name: pluralDraft, icon: iconDraft, color: colorDraft },
      rows.map((row) => ({ uuid: row.uuid, key: row.key, value_type: row.valueType })),
    );
  };
  useSaveShortcut(save, !pristine && !invalid);
  usePinTabOnEdit(workspace, !pristine);

  return (
    <div className="tab-content">
      <div className="type-actions-bar">
        <span className="dim type-header-title">
          Editing type
          {schema.embedded && (
            <span className="embedded-badge" title="Composition type — instances exist only as a property value of an owner object">
              embedded
            </span>
          )}
        </span>
        <div className="type-header-actions">
          <button
            className="button button-primary"
            disabled={pristine || invalid}
            title={invalid ? "Prop keys must be non-empty and unique" : undefined}
            onClick={save}
          >
            Save
          </button>
          <button
            className="button button-danger"
            onClick={() => void workspace.deleteType(schema.name)}
          >
            Delete type
          </button>
        </div>
      </div>
      <div className="type-header-boxes">
        <div className="type-field-box">
          <span className="type-field-box-label">Type name</span>
          <div className="type-field-box-content">
            <IconPicker
              icon={iconDraft}
              color={colorDraft}
              size={22}
              onUploadImage={(file) => workspace.uploadIconImage(file)}
              onChange={(icon, color) => {
                setIconDraft(icon);
                setColorDraft(color);
              }}
            />
            <input
              className="input type-name-input"
              value={nameDraft}
              onChange={(event) => setNameDraft(event.target.value)}
            />
          </div>
        </div>
        <div className="type-field-box">
          <span className="type-field-box-label">Type plural name</span>
          <div className="type-field-box-content">
            <input
              className="input type-name-input"
              placeholder="Name (plural)"
              value={pluralDraft}
              onChange={(event) => setPluralDraft(event.target.value)}
            />
          </div>
        </div>
      </div>
      {/* ADR-0013: attached traits as color-coded chips; attach from the
          remaining pool, detach only when the schema draft is pristine
          (detach hits the wire immediately, schema edits don't) */}
      <div className="type-traits-row">
        {schema.traits.map((name) => {
          const trait = state.traits.find((view) => view.name === name);
          return (
            <span className="trait-chip" key={name}>
              <span
                className="trait-dot"
                style={{ background: trait?.color ?? "var(--fg-dim)" }}
              />
              <button
                className="trait-chip-name"
                title="Open trait"
                onClick={() => workspace.openTrait(name)}
              >
                {name}
              </button>
              <button
                className="icon-button trait-chip-remove"
                title={`Detach ${name} — removes its props from every instance`}
                onClick={() => void workspace.detachTrait(schema.name, name)}
              >
                ×
              </button>
            </span>
          );
        })}
        <FloatingMenu
          wrapperClassName="trait-attach"
          triggerClassName="button trait-attach-trigger"
          menuClassName="type-menu"
          title="Attach trait"
          trigger={<span>+ Trait</span>}
        >
          {(close) => (
            <div className="type-menu-list">
              {state.traits.filter((trait) => !schema.traits.includes(trait.name))
                .length === 0 && (
                <div className="type-menu-empty dim">No traits to attach</div>
              )}
              {state.traits
                .filter((trait) => !schema.traits.includes(trait.name))
                .map((trait) => (
                  <button
                    key={trait.name}
                    className="type-menu-row"
                    onClick={() => {
                      void workspace.attachTrait(schema.name, trait.name);
                      close();
                    }}
                  >
                    <span className="trait-dot" style={{ background: trait.color }} />
                    <span>{trait.name}</span>
                  </button>
                ))}
            </div>
          )}
        </FloatingMenu>
      </div>
      <div className="schema-props">
        {rows.map((row, index) => {
          // the schema's first row is the pinned `name` title — no grip,
          // locked key and type, not draggable, not a drop target
          const pinned = index === 0 && row.key === "name";
          // ADR-0007: an existing scalar prop can carry a function-backed
          // value — the bind menu offers functions whose output matches.
          const schemaProp =
            row.uuid === null
              ? undefined
              : schema.props.find((prop) => prop.uuid === row.uuid);
          const boundUuid = schemaProp?.function_uuid ?? null;
          const boundName =
            boundUuid === null
              ? null
              : (state.functions.find((fn) => fn.uuid === boundUuid)?.name ?? null);
          const matchingFunctions = state.functions.filter((fn) => {
            const params = TypeNames.functionParams(fn.type_name);
            return params !== null && params.output === row.valueType;
          });
          return (
            <div
              key={row.uuid ?? `new-${index}`}
              className={rowClass(index)}
              draggable={!pinned}
              onDragStart={() => {
                if (!pinned) {
                  setDragIndex(index);
                }
              }}
              onDragOver={(event) => {
                if (pinned) {
                  return;
                }
                event.preventDefault();
                setOverIndex(index);
              }}
              onDragLeave={() => setOverIndex((current) => (current === index ? null : current))}
              onDrop={(event) => {
                if (!pinned) {
                  onDrop(event, index);
                }
              }}
              onDragEnd={() => {
                setDragIndex(null);
                setOverIndex(null);
              }}
            >
              {pinned ? (
                <span className="prop-grip prop-grip-spacer" title="The name prop is pinned first" />
              ) : (
                <span className="prop-grip" title="Drag to reorder">
                  <PropGrip />
                </span>
              )}
              {pinned ? (
                <>
                  <span className="schema-prop-key">name</span>
                  <span className="dim">String · title</span>
                </>
              ) : (
                <>
                  <input
                    className="input"
                    placeholder="Property Name"
                    value={row.key}
                    onChange={(event) => updateRow(index, { key: event.target.value })}
                  />
                  <TypePicker
                    workspace={workspace}
                    value={row.valueType}
                    onChange={(valueType) => updateRow(index, { valueType })}
                  />
                  {schemaProp !== undefined && TypeNames.isScalar(row.valueType) && (
                    <FunctionBindButton
                      bound={boundUuid !== null}
                      boundName={boundName}
                      functions={matchingFunctions}
                      onBind={(uuid) =>
                        void workspace.setPropFunction(schema.name, schemaProp.key, uuid)
                      }
                    />
                  )}
                  <button
                    className="icon-button"
                    title="Delete prop — removes it from every instance"
                    onClick={() =>
                      setRows((drafts) => drafts.filter((_, position) => position !== index))
                    }
                  >
                    ×
                  </button>
                </>
              )}
            </div>
          );
        })}
        {/* ADR-0013: trait-owned props — read-only rows tinted with the
            trait color; edit them on the trait page */}
        {schema.props
          .filter((prop) => prop.trait !== null)
          .map((prop) => (
            <div
              key={prop.uuid}
              className="prop-draft-row schema-prop-row schema-prop-row-trait"
              style={{ borderLeftColor: prop.trait_color ?? undefined }}
              title={`From trait ${prop.trait ?? ""} — edit on the trait page`}
            >
              <span className="prop-grip prop-grip-spacer" />
              <span className="schema-prop-key">{prop.key}</span>
              <span className="dim">
                {prop.value_type} · {prop.trait}
              </span>
            </div>
          ))}
      </div>
      <div className="type-create-actions">
        <button
          className="button"
          onClick={() =>
            setRows((drafts) => [
              ...drafts,
              { uuid: null, key: "", valueType: TypeNames.STRING },
            ])
          }
        >
          Add Property
        </button>
      </div>
    </div>
  );
}

/** ADR-0007: binds a Function<T,R> to a scalar prop (or unbinds it). The
 * menu lists every function whose output type equals the prop's value
 * type — the backend enforces the same match on save. */
function FunctionBindButton(props: {
  bound: boolean;
  boundName: string | null;
  functions: FunctionView[];
  onBind: (uuid: string | null) => void;
}): ReactElement {
  return (
    <FloatingMenu
      wrapperClassName="function-bind"
      triggerClassName={props.bound ? "function-bind-trigger bound" : "function-bind-trigger"}
      menuClassName="type-menu"
      title={props.bound ? `Bound to ${props.boundName ?? "function"}` : "Bind function"}
      trigger={
        <span className="function-bind-label">
          <span className="tab-function-icon">ƒ</span>
          {props.boundName !== null && <span className="function-bind-name">{props.boundName}</span>}
        </span>
      }
    >
      {(close) => (
        <div className="type-menu-list">
          {props.bound && (
            <button
              className="type-menu-row"
              onClick={() => {
                props.onBind(null);
                close();
              }}
            >
              Unbind
            </button>
          )}
          {props.functions.length === 0 && (
            <div className="type-menu-empty dim">No function with a matching output.</div>
          )}
          {props.functions.map((fn) => (
            <button
              key={fn.uuid}
              className="type-menu-row"
              onClick={() => {
                props.onBind(fn.uuid);
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
  );
}
