import type { ReactElement } from "react";
import { useEffect, useState } from "react";
import type { TraitView } from "../contracts";
import { TypeNames } from "../contracts";
import { useSaveShortcut } from "../state/use-save-shortcut";
import { usePinTabOnEdit } from "../state/use-pin-tab-on-edit";
import { WorkspaceStore } from "../state/workspace";
import { FloatingMenu } from "./floating-menu";
import { DEFAULT_COLOR, ICON_COLORS } from "./type-icon";
import { TypePicker } from "./type-picker";

/** One row of the trait editor's draft — uuid null marks a not-yet-created
 * prop; everything else is matched to the live trait by uuid. */
interface PropDraft {
  readonly uuid: string | null;
  readonly key: string;
  readonly valueType: string;
}

function draftsOf(trait: TraitView): PropDraft[] {
  return trait.props.map((prop) => ({
    uuid: prop.uuid,
    key: prop.key,
    valueType: prop.value_type,
  }));
}

/** Color-only chooser — traits have no icon, just the dot. Same swatch
 * palette the IconPicker uses. */
function TraitColorPicker(props: {
  color: string;
  onChange: (color: string) => void;
}): ReactElement {
  return (
    <FloatingMenu
      wrapperClassName="icon-picker"
      triggerClassName="icon-picker-trigger"
      menuClassName="icon-picker-menu"
      title="Trait color"
      trigger={<span className="trait-dot trait-dot-lg" style={{ background: props.color }} />}
    >
      {() => (
        <div className="icon-picker-swatches">
          {Object.entries(ICON_COLORS).map(([name, hex]) => (
            <button
              key={name}
              className={
                hex === props.color ? "icon-picker-swatch selected" : "icon-picker-swatch"
              }
              title={name}
              style={{ backgroundColor: hex }}
              onClick={() => props.onChange(hex)}
            />
          ))}
        </div>
      )}
    </FloatingMenu>
  );
}

/** ADR-0013: the trait page — name, color, prop rows. No pinned `name`
 * prop (a trait is a bundle, not an entity), no formulas (v1). The
 * "used by" list is read-only context so a delete attempt never
 * surprises. */
export function TraitPanel(props: {
  workspace: WorkspaceStore;
  trait: TraitView;
}): ReactElement {
  const { workspace, trait } = props;
  const [nameDraft, setNameDraft] = useState(trait.name);
  const [colorDraft, setColorDraft] = useState(trait.color);
  const [rows, setRows] = useState<PropDraft[]>(() => draftsOf(trait));

  useEffect(() => {
    setNameDraft(trait.name);
    setColorDraft(trait.color);
    setRows(draftsOf(trait));
  }, [trait]);

  const updateRow = (index: number, patch: Partial<PropDraft>): void => {
    setRows((drafts) =>
      drafts.map((draft, position) =>
        position === index ? { ...draft, ...patch } : draft,
      ),
    );
  };

  const pristine =
    nameDraft === trait.name &&
    colorDraft === trait.color &&
    JSON.stringify(rows) === JSON.stringify(draftsOf(trait));
  const keys = rows.map((row) => row.key);
  const invalid =
    keys.some((key) => key.trim() === "") ||
    new Set(keys).size !== keys.length ||
    nameDraft.trim() === "" ||
    TypeNames.isAny(nameDraft.trim());

  const save = (): void => {
    void workspace.saveTraitEdits(
      trait.name,
      { name: nameDraft.trim(), color: colorDraft },
      rows.map((row) => ({ uuid: row.uuid, key: row.key, value_type: row.valueType })),
    );
  };
  useSaveShortcut(save, !pristine && !invalid);
  usePinTabOnEdit(workspace, !pristine);

  return (
    <div className="tab-content">
      <div className="type-actions-bar">
        <span className="dim type-header-title">Editing trait</span>
        <div className="type-header-actions">
          <button
            className="button button-primary"
            disabled={pristine || invalid}
            title={invalid ? "Trait name and prop keys must be non-empty and unique" : undefined}
            onClick={save}
          >
            Save
          </button>
          <button
            className="button button-danger"
            title={
              trait.attached.length > 0
                ? `Attached to ${trait.attached.join(", ")} — detach first`
                : undefined
            }
            disabled={trait.attached.length > 0}
            onClick={() => void workspace.deleteTrait(trait.name)}
          >
            Delete trait
          </button>
        </div>
      </div>
      <div className="type-header-boxes">
        <div className="type-field-box">
          <span className="type-field-box-label">Trait name</span>
          <div className="type-field-box-content">
            <TraitColorPicker color={colorDraft} onChange={setColorDraft} />
            <input
              className="input type-name-input"
              value={nameDraft}
              onChange={(event) => setNameDraft(event.target.value)}
            />
          </div>
        </div>
        {trait.attached.length > 0 && (
          <div className="type-field-box">
            <span className="type-field-box-label">Attached to</span>
            <div className="type-field-box-content trait-attached-list">
              {trait.attached.map((name) => (
                <button
                  key={name}
                  className="trait-chip"
                  onClick={() => workspace.openType(name)}
                >
                  {name}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
      <div className="schema-props">
        {rows.map((row, index) => (
          <div key={row.uuid ?? `new-${index}`} className="prop-draft-row schema-prop-row">
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
            <button
              className="icon-button"
              title="Delete prop — removes it from every attached type's instances"
              onClick={() =>
                setRows((drafts) => drafts.filter((_, position) => position !== index))
              }
            >
              ×
            </button>
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

/** The create-trait form: name + color, props come after on the trait
 * page itself. */
export function TraitCreateForm(props: { workspace: WorkspaceStore }): ReactElement {
  const [name, setName] = useState("");
  const [color, setColor] = useState(DEFAULT_COLOR);
  const trimmed = name.trim();
  const invalid = trimmed === "" || TypeNames.isAny(trimmed);

  return (
    <div className="type-create-form">
      <div className="type-header-boxes">
        <div className="type-field-box">
          <span className="type-field-box-label">Trait name</span>
          <div className="type-field-box-content">
            <TraitColorPicker color={color} onChange={setColor} />
            <input
              className="input type-name-input"
              placeholder="Trait name"
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </div>
        </div>
      </div>
      <p className="dim">
        A trait is a reusable bundle of properties. Attach it to types; give
        props the <code>Any&lt;Trait&gt;</code> type to accept any object
        carrying it.
      </p>
      <div className="type-create-actions">
        <button
          className="button button-primary"
          disabled={invalid}
          onClick={() => void props.workspace.createTrait(trimmed, color)}
        >
          Create
        </button>
      </div>
    </div>
  );
}
