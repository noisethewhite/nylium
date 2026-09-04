import type { ReactElement } from "react";
import { useState } from "react";
import { WorkspaceStore } from "../state/workspace";
import { DEFAULT_COLOR, DEFAULT_ICON, IconPicker } from "./icon-picker";

interface SecondaryDraft {
  readonly name: string;
  readonly multiplier: string;
  readonly offset: string;
}

/** The create-unit tab: name + icon + the base part name + a list of
 * secondary parts, each with the affine factor
 * (base = (entered - offset) / multiplier). No props — a unit is a
 * conversion table, not a schema. */
export function UnitCreateForm(props: {
  workspace: WorkspaceStore;
}): ReactElement {
  const [name, setName] = useState("");
  const [icon, setIcon] = useState(DEFAULT_ICON);
  const [color, setColor] = useState(DEFAULT_COLOR);
  const [base, setBase] = useState("");
  const [secondaries, setSecondaries] = useState<SecondaryDraft[]>([]);

  const updateSecondary = (index: number, patch: Partial<SecondaryDraft>): void => {
    setSecondaries((drafts) =>
      drafts.map((draft, position) =>
        position === index ? { ...draft, ...patch } : draft,
      ),
    );
  };

  const secondaryNames = secondaries.map((row) => row.name.trim());
  const allNames = [base.trim(), ...secondaryNames].filter((part) => part !== "");
  const numericOk = secondaries.every(
    (row) =>
      !Number.isNaN(Number(row.multiplier)) &&
      row.multiplier.trim() !== "" &&
      Number(row.multiplier) !== 0 &&
      (row.offset.trim() === "" || !Number.isNaN(Number(row.offset))),
  );
  const invalid =
    name.trim() === "" ||
    base.trim() === "" ||
    new Set(allNames).size !== allNames.length ||
    !numericOk;

  const submit = (): void => {
    void props.workspace.createUnit(
      name.trim(),
      base.trim(),
      secondaries
        .filter((row) => row.name.trim() !== "")
        .map((row) => ({
          name: row.name.trim(),
          multiplier: Number(row.multiplier),
          offset: row.offset.trim() === "" ? 0 : Number(row.offset),
        })),
    );
  };

  return (
    <div className="type-create-form">
      <div className="type-header-boxes">
        <div className="type-field-box">
          <span className="type-field-box-label">Unit name</span>
          <div className="type-field-box-content">
            <IconPicker
              icon={icon}
              color={color}
              size={22}
              onChange={(nextIcon, nextColor) => {
                setIcon(nextIcon);
                setColor(nextColor);
              }}
            />
            <input
              className="input type-name-input"
              placeholder="Unit name"
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </div>
        </div>
        <div className="type-field-box">
          <span className="type-field-box-label">Base part</span>
          <div className="type-field-box-content">
            <input
              className="input"
              placeholder="e.g. °C, kg, m"
              value={base}
              onChange={(event) => setBase(event.target.value)}
            />
          </div>
        </div>
      </div>
      {secondaries.map((row, index) => (
        <div className="prop-draft-row" key={index}>
          <input
            className="input"
            placeholder="Part name (e.g. °F)"
            value={row.name}
            onChange={(event) => updateSecondary(index, { name: event.target.value })}
          />
          <input
            className="input"
            placeholder="Multiplier"
            inputMode="decimal"
            value={row.multiplier}
            onChange={(event) => updateSecondary(index, { multiplier: event.target.value })}
          />
          <input
            className="input"
            placeholder="Offset (0)"
            inputMode="decimal"
            value={row.offset}
            onChange={(event) => updateSecondary(index, { offset: event.target.value })}
          />
          <button
            className="icon-button"
            title="Remove part"
            onClick={() =>
              setSecondaries((drafts) => drafts.filter((_, position) => position !== index))
            }
          >
            ×
          </button>
        </div>
      ))}
      <div className="type-create-actions">
        <button
          className="button"
          onClick={() =>
            setSecondaries((drafts) => [
              ...drafts,
              { name: "", multiplier: "", offset: "" },
            ])
          }
        >
          Add Part
        </button>
        <button
          className="button button-primary"
          disabled={invalid}
          title={
            invalid
              ? "Name and base part required; part names unique; multiplier numeric and non-zero"
              : undefined
          }
          onClick={submit}
        >
          Create
        </button>
      </div>
    </div>
  );
}
