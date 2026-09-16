import type { ReactElement } from "react";
import { useEffect, useState } from "react";
import type { FormulaNode, FunctionView, TypeView } from "../contracts";
import { TypeNames } from "../contracts";
import { useObservable } from "../state/use-observable";
import { useSaveShortcut } from "../state/use-save-shortcut";
import { usePinTabOnEdit } from "../state/use-pin-tab-on-edit";
import { WorkspaceStore } from "../state/workspace";
import { CollectSelector } from "./collect-selector";
import { FloatingMenu } from "./floating-menu";
import { FormulaBlockEditor } from "./formula-block-editor";
import { IconPicker } from "./icon-picker";
import { Table } from "./table";

/** One row of the editor's draft — uuid null marks a not-yet-created
 * prop; everything else is matched to the live schema by uuid. */
interface PropDraft {
  readonly uuid: string | null;
  readonly key: string;
  readonly valueType: string;
  readonly formula: string | null;
  readonly collect: string | null;
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
      formula: prop.formula,
      collect: prop.collect,
    }));
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

  const moveRow = (from: number, to: number): void => {
    setRows((drafts) => {
      const moved = drafts[from];
      if (moved === undefined) {
        return drafts;
      }
      const next = drafts.filter((_, position) => position !== from);
      next.splice(to, 0, moved);
      return next;
    });
  };

  // the schema's first row is the pinned `name` title — locked key and
  // type, not draggable, not a drop target, no remove button
  const isPinned = (row: PropDraft, index: number): boolean =>
    index === 0 && row.key === "name";

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
      rows.map((row) => ({
        uuid: row.uuid,
        key: row.key,
        value_type: row.valueType,
        formula: row.formula,
        collect: row.collect,
      })),
    );
  };
  useSaveShortcut(save, !pristine && !invalid);
  usePinTabOnEdit(workspace, !pristine);

  return (
    <div className="editor-shell">
      <div className="editor-header">
        <span className="dim editor-header-title">
          Editing type
          {schema.embedded && (
            <span className="embedded-badge" title="Composition type — instances exist only as a property value of an owner object">
              embedded
            </span>
          )}
        </span>
        <div className="editor-actions">
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
      <div className="editor-boxes">
        <div className="editor-box">
          <span className="editor-box-label">Type name</span>
          <div className="editor-box-content">
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
        <div className="editor-box">
          <span className="editor-box-label">Type plural name</span>
          <div className="editor-box-content">
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
      <Table
        rows={rows}
        keyOf={(row, index) => row.uuid ?? `new-${index}`}
        locked={isPinned}
        onReorder={moveRow}
        columns={[
          { kind: "drag" },
          {
            kind: "string",
            placeholder: "Property Name",
            value: (row) => row.key,
            onEdit: (row, value, index) => updateRow(index, { key: value }),
          },
          {
            kind: "type-selector",
            workspace,
            value: (row) => row.valueType,
            display: (row, index) =>
              isPinned(row, index) ? <span className="dim">String · title</span> : undefined,
            onPick: (row, value, index) => updateRow(index, { valueType: value }),
          },
          {
            kind: "remove",
            title: "Delete prop — removes it from every instance",
            visible: (row, index) => !isPinned(row, index),
            onRemove: (index) =>
              setRows((drafts) => drafts.filter((_, position) => position !== index)),
          },
        ]}
        rowExtra={(row, index) => {
          if (isPinned(row, index)) {
            return null;
          }
          const schemaProp =
            row.uuid === null
              ? undefined
              : schema.props.find((prop) => prop.uuid === row.uuid);
          if (schemaProp === undefined) {
            return null;
          }
          const scalar = TypeNames.isScalar(row.valueType);
          const array = TypeNames.isArray(row.valueType);
          return (
            <>
              {scalar && (
                <>
                  <FunctionBindButton
                    bound={schemaProp.function_uuid !== null}
                    boundName={
                      state.functions.find((fn) => fn.uuid === schemaProp.function_uuid)?.name ??
                      null
                    }
                    functions={state.functions.filter((fn) => {
                      const params = TypeNames.functionParams(fn.type_name);
                      return params !== null && params.output === row.valueType;
                    })}
                    onBind={(uuid) =>
                      void workspace.setPropFunction(schema.name, schemaProp.key, uuid)
                    }
                  />
                  <FormulaBindButton
                    formula={row.formula}
                    schema={schema}
                    types={state.types}
                    parse={(formula) => workspace.parseFormula(formula)}
                    onChange={(formula) => updateRow(index, { formula })}
                  />
                </>
              )}
              {array && (
                <CollectSelector
                  valueType={row.valueType}
                  collect={row.collect}
                  onChange={(collect) => updateRow(index, { collect })}
                  types={state.types}
                />
              )}
            </>
          );
        }}
        trailing={
          /* ADR-0013: trait-owned props — read-only rows tinted with the
             trait color; edit them on the trait page */
          <>
            {schema.props
              .filter((prop) => prop.trait !== null)
              .map((prop) => (
                <div
                  key={prop.uuid}
                  className="table-row table-row-trait"
                  style={{ borderLeftColor: prop.trait_color ?? undefined }}
                  title={`From trait ${prop.trait ?? ""} — edit on the trait page`}
                >
                  <span className="table-grip table-grip-spacer" />
                  <span className="table-cell-static">{prop.key}</span>
                  <span className="dim">
                    {prop.value_type} · {prop.trait}
                  </span>
                </div>
              ))}
          </>
        }
      />
      <div className="editor-footer">
        <button
          className="button"
          onClick={() =>
            setRows((drafts) => [
              ...drafts,
              { uuid: null, key: "", valueType: TypeNames.STRING, formula: null, collect: null },
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

/** ADR-0026: opens the block-based formula editor for a scalar prop. The
 * stored text is parsed to blocks on open and re-rendered to text on every
 * edit; the backend validates the text on save. */
function FormulaBindButton(props: {
  formula: string | null;
  schema: TypeView;
  types: readonly TypeView[];
  parse: (formula: string) => Promise<FormulaNode>;
  onChange: (formula: string | null) => void;
}): ReactElement {
  const bound = props.formula !== null;
  return (
    <FloatingMenu
      wrapperClassName="function-bind"
      triggerClassName={bound ? "function-bind-trigger bound" : "function-bind-trigger"}
      menuClassName="formula-menu"
      title={bound ? "Edit formula" : "Add formula"}
      trigger={
        <span className="function-bind-label">
          <span className="tab-function-icon">ƒx</span>
          {bound && <span className="function-bind-name">formula</span>}
        </span>
      }
    >
      {() => (
        <FormulaBlockEditor
          formula={props.formula}
          onChange={props.onChange}
          schema={props.schema}
          types={props.types}
          parse={props.parse}
        />
      )}
    </FloatingMenu>
  );
}
