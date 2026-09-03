import type { ReactElement } from "react";
import { useObservable } from "../state/use-observable";
import type { Tab } from "../state/workspace";
import { sameTab, WorkspaceStore } from "../state/workspace";
import { ObjectLabels } from "./object-labels";
import { TypeIcon } from "./type-icon";

export function TabBar(props: { workspace: WorkspaceStore }): ReactElement {
  const state = useObservable(props.workspace);

  const labelOf = (tab: Tab): string => {
    if (tab.kind === "type") {
      return tab.name;
    }
    if (tab.kind === "create-type") {
      return "New Type";
    }
    if (tab.kind === "create-enum") {
      return "New Enum";
    }
    const object = state.objects.find((view) => view.uuid === tab.uuid);
    return object === undefined ? tab.uuid.slice(0, 8) : ObjectLabels.of(object);
  };

  const iconOf = (tab: Tab): ReactElement | null => {
    if (tab.kind === "type") {
      const view = state.types.find((type) => type.name === tab.name);
      if (view === undefined) {
        return null;
      }
      return <TypeIcon icon={view.icon} color={view.color} size={14} />;
    }
    if (tab.kind === "object") {
      const object = state.objects.find((view) => view.uuid === tab.uuid);
      const type =
        object === undefined
          ? undefined
          : state.types.find((view) => view.name === object.type_name);
      if (type === undefined) {
        return null;
      }
      return <TypeIcon icon={type.icon} color={type.color} size={14} />;
    }
    return null;
  };

  const activate = (tab: Tab): void => {
    if (tab.kind === "type") {
      props.workspace.openType(tab.name);
      return;
    }
    if (tab.kind === "object") {
      props.workspace.openObject(tab.uuid);
      return;
    }
    if (tab.kind === "create-enum") {
      props.workspace.openCreateEnum();
      return;
    }
    props.workspace.openCreateType();
  };

  return (
    <div className="tab-bar">
      {state.tabs.map((tab, index) => (
        <div
          key={index}
          className={
            state.activeTab !== null && sameTab(state.activeTab, tab)
              ? "tab tab-active"
              : "tab"
          }
        >
          <button className="tab-label" onClick={() => activate(tab)}>
            {iconOf(tab)}
            <span>{labelOf(tab)}</span>
          </button>
          <button
            className="icon-button tab-close"
            title="Close tab"
            onClick={() => props.workspace.closeTab(tab)}
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
}
