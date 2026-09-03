import type { ReactElement } from "react";
import { useState } from "react";
import { FloatingMenu } from "./floating-menu";
import { DEFAULT_COLOR, DEFAULT_ICON, ICON_COLORS, ICON_NAMES, TypeIcon } from "./type-icon";

/** Icon + color chooser popover, used in the type editor header and the
 * create-type form. Click the glyph to open; pick an icon from the
 * filterable grid and a swatch below. */
export function IconPicker(props: {
  icon: string;
  color: string;
  onChange: (icon: string, color: string) => void;
  size?: number;
}): ReactElement {
  const [query, setQuery] = useState("");

  const shown = ICON_NAMES.filter((name) => name.includes(query.toLowerCase()));

  return (
    <FloatingMenu
      wrapperClassName="icon-picker"
      triggerClassName="icon-picker-trigger"
      menuClassName="icon-picker-menu"
      title="Icon & color"
      trigger={<TypeIcon icon={props.icon} color={props.color} size={props.size ?? 20} />}
    >
      {() => (
        <>
          <input
            className="input icon-picker-search"
            placeholder="Click to filter..."
            value={query}
            autoFocus
            onChange={(event) => setQuery(event.target.value)}
          />
          <div className="icon-picker-grid">
            {shown.map((name) => (
              <button
                key={name}
                className={
                  name === props.icon
                    ? "icon-picker-cell selected"
                    : "icon-picker-cell"
                }
                title={name}
                onClick={() => props.onChange(name, props.color)}
              >
                <TypeIcon icon={name} color={props.color} size={18} />
              </button>
            ))}
            {shown.length === 0 && (
              <div className="type-menu-empty dim">No icons</div>
            )}
          </div>
          <div className="icon-picker-swatches">
            {Object.entries(ICON_COLORS).map(([name, hex]) => (
              <button
                key={name}
                className={
                  name === props.color
                    ? "icon-picker-swatch selected"
                    : "icon-picker-swatch"
                }
                title={name}
                style={{ backgroundColor: hex }}
                onClick={() => props.onChange(props.icon, name)}
              />
            ))}
          </div>
        </>
      )}
    </FloatingMenu>
  );
}

export { DEFAULT_COLOR, DEFAULT_ICON };
