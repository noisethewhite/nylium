import type { ReactElement } from "react";
import { useEffect, useState } from "react";
import type { TypeView } from "../contracts";
import { useSaveShortcut } from "../state/use-save-shortcut";
import { WorkspaceStore } from "../state/workspace";
import { IconPicker } from "./icon-picker";

/** One row of the unit part draft — uuid null marks a not-yet-created
 * part; an existing uuid with a changed name is a rename that the
 * backend propagates into every stored unit label. multiplier/offset
 * stay strings while editing so intermediate text survives. */
interface PartDraft {
  readonly uuid: string | null;
  readonly name: string;
  readonly multiplier: string;
  readonly offset: string;
  readonly is_base: boolean;
}

function draftsOf(schema: TypeView): PartDraft[] {
  return schema.unit_parts.map((part) => ({
    uuid: part.uuid,
    name: part.name,
    multiplier: part.multiplier,
    offset: part.offset,
    is_base: part.is_base,
  }));
}

/** The unit page: same chrome as the enum page, but the body edits
 * parts — each with the affine factor
 * (base = (entered - offset) / multiplier). Exactly one base part;
 * its factor is fixed at multiplier 1, offset 0. */
export function UnitTypePanel(props: {
  workspace: WorkspaceStore;
  schema: TypeView;
}): ReactElement {
  const { workspace, schema } = props;
  const [nameDraft, setNameDraft] = useState(schema.name);
  const [iconDraft, setIconDraft] = useState(schema.icon);
  const [colorDraft, setColorDraft] = useState(schema.color);
  const [rows, setRows] = useState<PartDraft[]>(() => draftsOf(schema));

  useEffect(() => {
    setNameDraft(schema.name);
    setIconDraft(schema.icon);
    setColorDraft(schema.color);
    setRows(draftsOf(schema));
  }, [schema]);

  const updateRow = (index: number, patch: Partial<PartDraft>): void => {
    setRows((drafts) =>
      drafts.map((draft, position) =>
        position === index ? { ...draft, ...patch } : draft,
      ),
    );
  };

  const pristine =
    nameDraft === schema.name &&
    iconDraft === schema.icon &&
    colorDraft === schema.color &&
    JSON.stringify(rows) === JSON.stringify(draftsOf(schema));
  const names = rows.map((row) => row.name.trim()).filter((name) => name !== "");
  const factorsOk = rows.every(
    (row) =>
      row.is_base ||
      (!Number.isNaN(Number(row.multiplier)) &&
        row.multiplier.trim() !== "" &&
        Number(row.multiplier) !== 0 &&
        (row.offset.trim() === "" || !Number.isNaN(Number(row.offset)))),
  );
  const baseCount = rows.filter((row) => row.is_base).length;
  const invalid =
    nameDraft.trim() === "" ||
    new Set(names).size !== names.length ||
    names.length === 0 ||
    baseCount !== 1 ||
    !factorsOk;

  const save = (): void => {
    void workspace.saveUnitEdits(
      schema.name,
      { name: nameDraft.trim(), icon: iconDraft, color: colorDraft },
      rows
        .filter((row) => row.name.trim() !== "")
        .map((row) => ({
          uuid: row.uuid,
          name: row.name.trim(),
          multiplier: row.is_base ? 1 : Number(row.multiplier),
          offset: row.is_base ? 0 : row.offset.trim() === "" ? 0 : Number(row.offset),
          is_base: row.is_base,
        })),
    );
  };
  useSaveShortcut(save, !pristine && !invalid);

  return (
    <div className="tab-content">
      <div className="type-actions-bar">
        <span className="dim type-header-title">Editing unit</span>
        <div className="type-header-actions">
          <button
            className="button button-primary"
            disabled={pristine || invalid}
            title={
              invalid
                ? "Part names unique, exactly one base part, secondary multipliers numeric and non-zero"
                : undefined
            }
            onClick={save}
          >
            Save
          </button>
          <button
            className="button button-danger"
            onClick={() => void workspace.deleteType(schema.name)}
          >
            Delete unit
          </button>
        </div>
      </div>
      <div className="type-header-boxes">
        <div className="type-field-box">
          <span className="type-field-box-label">Unit name</span>
          <div className="type-field-box-content">
            <IconPicker
              icon={iconDraft}
              color={colorDraft}
              size={22}
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
      </div>
      <div className="schema-props">
        {rows.map((row, index) => (
          <div key={row.uuid ?? `new-${index}`} className="prop-draft-row">
            <input
              type="radio"
              name="unit-base"
              title="Base part — stored values are kept in this part"
              checked={row.is_base}
              onChange={() =>
                setRows((drafts) =>
                  drafts.map((draft, position) => ({
                    ...draft,
                    is_base: position === index,
                  })),
                )
              }
            />
            <input
              className="input"
              placeholder="Part name"
              value={row.name}
              onChange={(event) => updateRow(index, { name: event.target.value })}
            />
            {!row.is_base && (
              <>
                <input
                  className="input"
                  placeholder="Multiplier"
                  inputMode="decimal"
                  value={row.multiplier}
                  onChange={(event) => updateRow(index, { multiplier: event.target.value })}
                />
                <input
                  className="input"
                  placeholder="Offset (0)"
                  inputMode="decimal"
                  value={row.offset}
                  onChange={(event) => updateRow(index, { offset: event.target.value })}
                />
              </>
            )}
            <button
              className="icon-button"
              title="Delete part — refused while any value uses it"
              disabled={rows.length <= 1}
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
              { uuid: null, name: "", multiplier: "", offset: "", is_base: false },
            ])
          }
        >
          Add Part
        </button>
      </div>
    </div>
  );
}
