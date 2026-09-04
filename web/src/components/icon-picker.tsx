import type { ReactElement } from "react";
import { useRef, useState } from "react";
import { FloatingMenu } from "./floating-menu";
import { TypeNames } from "../contracts";
import { DEFAULT_COLOR, DEFAULT_ICON, ICON_COLORS, ICON_NAMES, TypeIcon } from "./type-icon";

/** Icon + color chooser popover, used in the type editor header and the
 * create-type form. Click the glyph to open; pick an icon from the
 * filterable grid and a swatch below. When `onUploadImage` is given, an
 * extra row lets the user upload an Image blob as the icon (ADR-0006) —
 * the callback receives the file and returns the `img:<uuid>` value. */
export function IconPicker(props: {
  icon: string;
  color: string;
  onChange: (icon: string, color: string) => void;
  onUploadImage?: (file: File) => Promise<string>;
  size?: number;
}): ReactElement {
  const [query, setQuery] = useState("");
  const imageInput = useRef<HTMLInputElement | null>(null);

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
          {props.onUploadImage !== undefined && (
            <div className="icon-picker-upload-row">
              <input
                ref={imageInput}
                type="file"
                accept="image/*"
                hidden
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  event.target.value = "";
                  if (file !== undefined && props.onUploadImage !== undefined) {
                    void props.onUploadImage(file).then((icon) =>
                      props.onChange(icon, props.color),
                    );
                  }
                }}
              />
              <button
                className="type-menu-row"
                onClick={() => imageInput.current?.click()}
              >
                Upload image…
              </button>
              {props.icon.startsWith(TypeNames.IMG_ICON_PREFIX) && (
                <button
                  className="type-menu-row"
                  onClick={() => props.onChange(DEFAULT_ICON, props.color)}
                >
                  Back to glyph
                </button>
              )}
            </div>
          )}
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
                  hex === props.color
                    ? "icon-picker-swatch selected"
                    : "icon-picker-swatch"
                }
                title={name}
                style={{ backgroundColor: hex }}
                onClick={() => props.onChange(props.icon, hex)}
              />
            ))}
          </div>
        </>
      )}
    </FloatingMenu>
  );
}

export { DEFAULT_COLOR, DEFAULT_ICON };
