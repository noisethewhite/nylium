import type { ReactElement } from "react";
import { useEffect } from "react";
import { AuthStore } from "../state/auth";
import { useObservable } from "../state/use-observable";
import { WorkspaceStore } from "../state/workspace";
import { LoginView } from "./login-view";
import { Sidebar } from "./sidebar";
import { TypePanel } from "./type-panel";

export function App(props: {
  workspace: WorkspaceStore;
  auth: AuthStore;
}): ReactElement {
  const authState = useObservable(props.auth);
  const state = useObservable(props.workspace);
  const schema = props.workspace.selectedType();

  useEffect(() => {
    if (authState.status === "authenticated") {
      void props.workspace.init();
    }
  }, [authState.status, props.workspace]);

  if (authState.status === "loading") {
    return <div className="app-loading">…</div>;
  }
  if (authState.status === "anonymous") {
    return <LoginView auth={props.auth} />;
  }

  return (
    <div className="app">
      <Sidebar workspace={props.workspace} auth={props.auth} />
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
