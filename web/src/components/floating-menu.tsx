import type { ReactElement, ReactNode } from "react";
import { useEffect, useState } from "react";

/** Every popover in the app: a trigger button plus a menu that floats
 * below it over a click-away backdrop. Owns open/close state; menu
 * content gets `close` to dismiss itself after a pick. Positioning and
 * chrome come from the caller's `menuClassName`. */
export function FloatingMenu(props: {
  trigger: ReactNode;
  title?: string;
  wrapperClassName?: string;
  triggerClassName?: string;
  menuClassName?: string;
  children: (close: () => void) => ReactNode;
}): ReactElement {
  const [open, setOpen] = useState(false);
  const close = (): void => setOpen(false);
  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent): void => {
      if (event.key === "Escape") close();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open]);
  return (
    <div className={`floating-menu ${props.wrapperClassName ?? ""}`}>
      <button
        className={props.triggerClassName ?? "icon-button"}
        title={props.title}
        onClick={() => (open ? close() : setOpen(true))}
      >
        {props.trigger}
      </button>
      {open && (
        <>
          <div className="floating-menu-backdrop" onClick={close} />
          <div className={props.menuClassName ?? "type-menu"}>
            {props.children(close)}
          </div>
        </>
      )}
    </div>
  );
}
