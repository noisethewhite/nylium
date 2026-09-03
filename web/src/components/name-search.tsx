import type { ReactElement, ReactNode } from "react";
import { useState } from "react";

/** The single name-filtered pick list — every "choose an object / type /
 * option" control renders this inside a FloatingMenu. Generic over the
 * item type; callers describe how to key, label and iconify an item.
 * `onUnset` adds a leading "—" row for nullable picks. */
export function NameSearch<T>(props: {
  items: readonly T[];
  getKey: (item: T) => string;
  getLabel: (item: T) => string;
  onPick: (item: T) => void;
  renderIcon?: (item: T) => ReactNode;
  placeholder?: string;
  emptyLabel?: string;
  unsetLabel?: string;
  onUnset?: () => void;
  header?: ReactNode;
}): ReactElement {
  const [query, setQuery] = useState("");
  const needle = query.toLowerCase();
  const matches = props.items.filter((item) =>
    props.getLabel(item).toLowerCase().includes(needle),
  );
  return (
    <>
      {props.header}
      <div className="type-menu-search">
        <input
          className="input"
          placeholder={props.placeholder ?? "Search…"}
          value={query}
          autoFocus
          onChange={(event) => setQuery(event.target.value)}
        />
      </div>
      <div className="type-menu-list">
        {props.onUnset !== undefined && (
          <button className="type-menu-row" onClick={props.onUnset}>
            <span className="dim">{props.unsetLabel ?? "—"}</span>
          </button>
        )}
        {matches.map((item) => (
          <button
            key={props.getKey(item)}
            className="type-menu-row"
            onClick={() => props.onPick(item)}
          >
            {props.renderIcon?.(item)}
            <span>{props.getLabel(item)}</span>
          </button>
        ))}
        {matches.length === 0 && (
          <div className="type-menu-empty dim">
            {props.emptyLabel ?? "Nothing found"}
          </div>
        )}
      </div>
    </>
  );
}
