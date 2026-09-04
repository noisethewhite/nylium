import { useEffect, useRef } from "react";

/** Cmd+S / Ctrl+S saves the mounted editor. Only the active tab is
 * rendered, so a window-level listener never fires for a hidden view.
 * `enabled` mirrors the Save button's disabled state — a pristine or
 * invalid form ignores the shortcut exactly like it ignores the click. */
export function useSaveShortcut(save: () => void, enabled: boolean): void {
  // the save closure re-creates every render (it captures drafts);
  // a ref keeps the listener stable across keystrokes
  const saveRef = useRef(save);
  saveRef.current = save;

  useEffect(() => {
    if (!enabled) {
      return;
    }
    const onKeyDown = (event: KeyboardEvent): void => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "s") {
        event.preventDefault();
        saveRef.current();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [enabled]);
}
