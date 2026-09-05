import type { ReactElement } from "react";
import { WorkspaceStore } from "../state/workspace";
import { FloatingMenu } from "./floating-menu";
import { NameSearch } from "./name-search";
import { TypeIcon } from "./type-icon";

/** A narrow name-search picker over a fixed list of type names — the
 * function editor's input/output/cast selectors. Lighter than TypePicker:
 * no submenus, just a search box over a caller-supplied set of names. */
export function TypeSelect(props: {
  workspace: WorkspaceStore;
  value: string;
  options: readonly string[];
  onChange: (value: string) => void;
  /** When set, a leading "—" row clears the value back to "". */
  emptyLabel?: string;
  placeholder?: string;
  triggerClassName?: string;
}): ReactElement {
  const iconOf = (name: string): ReactElement => {
    const view = props.workspace.typeView(name);
    return (
      <TypeIcon icon={view?.icon ?? "inventory_2"} color={view?.color ?? "gray"} size={15} />
    );
  };
  const current = props.workspace.typeView(props.value);
  return (
    <FloatingMenu
      wrapperClassName="type-picker floating-menu-grow"
      triggerClassName={props.triggerClassName ?? "input type-picker-trigger"}
      menuClassName="type-menu"
      trigger={
        <>
          <span className="material-symbols-outlined type-picker-chevron" aria-hidden>
            keyboard_arrow_down
          </span>
          <TypeIcon
            icon={current?.icon ?? "inventory_2"}
            color={current?.color ?? "gray"}
            size={15}
          />
          <span className="type-picker-value">{props.value === "" ? "—" : props.value}</span>
        </>
      }
    >
      {(close) => (
        <NameSearch
          items={props.options}
          getKey={(name) => name}
          getLabel={(name) => name}
          renderIcon={(name) => iconOf(name)}
          placeholder={props.placeholder ?? "Search types…"}
          emptyLabel="Nothing found"
          {...(props.emptyLabel === undefined
            ? {}
            : {
                onUnset: () => {
                  props.onChange("");
                  close();
                },
                unsetLabel: props.emptyLabel,
              })}
          onPick={(name) => {
            props.onChange(name);
            close();
          }}
        />
      )}
    </FloatingMenu>
  );
}
