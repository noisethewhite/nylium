import type { ReactElement } from "react";
import { useObservable } from "../state/use-observable";
import { WorkspaceStore } from "../state/workspace";
import { Sidebar } from "./sidebar";
import { TypePanel } from "./type-panel";

export function App(props: { workspace: WorkspaceStore }): ReactElement {
  const state = useObservable(props.workspace);
  const schema = props.workspace.selectedType();

  return (
    <div className="app">
      <Sidebar workspace={props.workspace} />
      <main className="main">
        {state.error !== null && <div className="error-banner">{state.error}</div>}
        {state.loading && <div className="empty-state">loading…</div>}
        {!state.loading && schema === null && (
          <div className="empty-state">
            <p>No types yet.</p>
            <p className="dim">Create one in the sidebar.</p>
          </div>
        )}
        {!state.loading && schema !== null && (
          <TypePanel workspace={props.workspace} schema={schema} />
        )}
      </main>
    </div>
  );
}
