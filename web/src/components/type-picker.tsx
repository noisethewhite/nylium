import type { ReactElement } from "react";
import { useState } from "react";
import { TypeLabels, TypeNames } from "../contracts";
import { WorkspaceStore } from "../state/workspace";

/** Submenu the two bottom buttons open — same view, different wrapping. */
type ObjectMode = "single" | "array";

/** Scalars listed flat in the menu — the calendar family hides behind
 * its own submenu so five variants don't flood the list. */
const FLAT_SCALARS = [TypeNames.STRING, TypeNames.INTEGER, TypeNames.NUMERIC, TypeNames.BOOLEAN];

export function TypePicker(props: {
  workspace: WorkspaceStore;
  value: string;
  onChange: (value: string) => void;
}): ReactElement {
  const [open, setOpen] = useState(false);
  const [objectMode, setObjectMode] = useState<ObjectMode | null>(null);
  const [calendarOpen, setCalendarOpen] = useState(false);
  const [query, setQuery] = useState("");

  const close = (): void => {
    setOpen(false);
    setObjectMode(null);
    setCalendarOpen(false);
    setQuery("");
  };

  const pick = (value: string): void => {
    props.onChange(value);
    close();
  };

  const matches = props.workspace
    .userTypes()
    .filter((view) => view.name.toLowerCase().includes(query.toLowerCase()));

  const renderObjectSearch = (mode: ObjectMode): ReactElement => (
    <>
      <div className="type-menu-search">
        <button className="icon-button" title="Back" onClick={() => setObjectMode(null)}>
          ←
        </button>
        <input
          className="input"
          placeholder="Search types…"
          value={query}
          autoFocus
          onChange={(event) => setQuery(event.target.value)}
        />
      </div>
      <div className="type-menu-list">
        {matches.map((view) => (
          <button
            key={view.name}
            className="type-menu-row"
            onClick={() =>
              pick(mode === "array" ? TypeNames.arrayOf(view.name) : view.name)
            }
          >
            {mode === "array" ? TypeNames.arrayOf(view.name) : view.name}
          </button>
        ))}
        {matches.length === 0 && <div className="type-menu-empty dim">No types</div>}
      </div>
    </>
  );

  const renderCalendar = (): ReactElement => (
    <>
      <div className="type-menu-search">
        <button className="icon-button" title="Back" onClick={() => setCalendarOpen(false)}>
          ←
        </button>
        <span className="dim type-menu-title">Date &amp; time</span>
      </div>
      <div className="type-menu-list">
        {TypeNames.CALENDAR.map((name) => (
          <button key={name} className="type-menu-row" onClick={() => pick(name)}>
            {TypeLabels[name] ?? name}
          </button>
        ))}
      </div>
    </>
  );

  return (
    <div className="type-picker">
      <button
        className="input type-picker-trigger"
        onClick={() => (open ? close() : setOpen(true))}
      >
        {props.value}
      </button>
      {open && (
        <>
          <div className="type-picker-backdrop" onClick={close} />
          <div className="type-menu">
            {objectMode !== null ? (
              renderObjectSearch(objectMode)
            ) : calendarOpen ? (
              renderCalendar()
            ) : (
              <>
                <div className="type-menu-list">
                  {FLAT_SCALARS.map((scalar) => (
                    <button
                      key={scalar}
                      className="type-menu-row"
                      onClick={() => pick(scalar)}
                    >
                      {scalar}
                    </button>
                  ))}
                  <button
                    className="type-menu-row"
                    onClick={() => setCalendarOpen(true)}
                  >
                    Date &amp; time →
                  </button>
                </div>
                <div className="type-menu-divider" />
                <div className="type-menu-footer">
                  <button
                    className="type-menu-row"
                    onClick={() => setObjectMode("single")}
                  >
                    Object
                  </button>
                  <button
                    className="type-menu-row"
                    onClick={() => setObjectMode("array")}
                  >
                    Array of objects
                  </button>
                </div>
              </>
            )}
          </div>
        </>
      )}
    </div>
  );
}
