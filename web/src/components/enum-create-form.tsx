import type { ReactElement } from "react";
import { useState } from "react";
import { WorkspaceStore } from "../state/workspace";
import { DEFAULT_COLOR, DEFAULT_ICON, IconPicker } from "./icon-picker";

/** The create-enum tab: name + icon + a flat list of option strings.
 * No plural name, no props — an enum is a list, not a schema. */
export function EnumCreateForm(props: {
  workspace: WorkspaceStore;
}): ReactElement {
  const [name, setName] = useState("");
  const [icon, setIcon] = useState(DEFAULT_ICON);
  const [color, setColor] = useState(DEFAULT_COLOR);
  const [options, setOptions] = useState<string[]>([""]);

  const updateOption = (index: number, value: string): void => {
    setOptions((drafts) =>
      drafts.map((draft, position) => (position === index ? value : draft)),
    );
  };

  const trimmed = options.map((option) => option.trim()).filter((option) => option !== "");
  const unique = new Set(trimmed);
  const invalid = name.trim() === "" || unique.size !== trimmed.length;

  const submit = (): void => {
    void props.workspace.createEnum(name.trim(), trimmed);
  };

  return (
    <div className="type-create-form">
      <div className="type-header">
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
          placeholder="Enum name"
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
      </div>
      {options.map((option, index) => (
        <div className="prop-draft-row" key={index}>
          <input
            className="input"
            placeholder="Option"
            value={option}
            onChange={(event) => updateOption(index, event.target.value)}
          />
          <button
            className="icon-button"
            title="Remove option"
            onClick={() =>
              setOptions((drafts) => drafts.filter((_, position) => position !== index))
            }
          >
            ×
          </button>
        </div>
      ))}
      <div className="type-create-actions">
        <button className="button" onClick={() => setOptions((drafts) => [...drafts, ""])}>
          Add Option
        </button>
        <button
          className="button button-primary"
          disabled={invalid}
          title={invalid ? "Options must be unique and the name non-empty" : undefined}
          onClick={submit}
        >
          Create
        </button>
      </div>
    </div>
  );
}
