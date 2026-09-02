import type { ReactElement } from "react";
import { useObservable } from "../state/use-observable";
import type { Tab } from "../state/workspace";
import { sameTab, WorkspaceStore } from "../state/workspace";
import { ObjectLabels } from "./object-labels";

export function TabBar(props: { workspace: WorkspaceStore }): ReactElement {
  const state = useObservable(props.workspace);

  const labelOf = (tab: Tab): string => {
    if (tab.kind === "type") {
      return tab.name;
    }
    if (tab.kind === "create-type") {
      return "New Type";
    }
    const object = state.objects.find((view) => view.uuid === tab.uuid);
    return object === undefined ? tab.uuid.slice(0, 8) : ObjectLabels.of(object);
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
            {labelOf(tab)}
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
