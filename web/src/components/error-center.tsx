import type { ReactElement } from "react";
import { useEffect, useState } from "react";
import type { ErrorEntry, ErrorStore } from "../state/errors";
import { useObservable } from "../state/use-observable";

const TOAST_TTL_MS = 5000;

/** One floating error: semi-transparent, fades away after a few
 * seconds. Hovering freezes it — opaque, framed — and moving the
 * mouse away dismisses it into the log. */
function ErrorToast(props: {
  entry: ErrorEntry;
  errors: ErrorStore;
}): ReactElement {
  const [hovered, setHovered] = useState(false);
  const { entry, errors } = props;

  useEffect(() => {
    if (hovered) {
      return;
    }
    const timer = setTimeout(() => errors.dismissToast(entry.id), TOAST_TTL_MS);
    return () => clearTimeout(timer);
  }, [hovered, errors, entry.id]);

  return (
    <div
      className={hovered ? "error-toast error-toast-hovered" : "error-toast"}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => errors.dismissToast(entry.id)}
    >
      {entry.message}
    </div>
  );
}

/** Top-right corner: a count button opening the error log, plus the
 * stack of live toasts. Toasts vanish on hover-out or when the log
 * opens; the log keeps everything until cleared. */
export function ErrorCenter(props: { errors: ErrorStore }): ReactElement {
  const { errors } = props;
  const state = useObservable(errors);
  const toastEntries = state.toasts
    .map((id) => state.entries.find((entry) => entry.id === id))
    .filter((entry): entry is ErrorEntry => entry !== undefined);

  return (
    <div className="error-center">
      {toastEntries.map((entry) => (
        <ErrorToast key={entry.id} entry={entry} errors={errors} />
      ))}
      <button
        className={
          state.entries.length > 0
            ? "error-count-button error-count-button-active"
            : "error-count-button"
        }
        onClick={() => errors.togglePanel()}
        title="Error log"
      >
        ⚠ {state.entries.length}
      </button>
      {state.panelOpen && (
        <div className="error-log-panel">
          <div className="error-log-head">
            <span>Errors</span>
            <button className="icon-button" onClick={() => errors.clear()}>
              Clear
            </button>
          </div>
          {state.entries.length === 0 && (
            <div className="error-log-empty dim">No errors yet.</div>
          )}
          {[...state.entries].reverse().map((entry) => (
            <div key={entry.id} className="error-log-entry">
              <span className="error-log-time">
                {entry.at.toLocaleTimeString()}
              </span>
              <span>{entry.message}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
