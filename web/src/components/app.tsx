import type { ReactElement } from "react";
import { useEffect } from "react";
import { AuthStore } from "../state/auth";
import { useObservable } from "../state/use-observable";
import { WorkspaceStore } from "../state/workspace";
import { LoginView } from "./login-view";
import { ObjectEditor } from "./object-editor";
import { Sidebar } from "./sidebar";
import { TabBar } from "./tab-bar";
import { TypeCreateForm } from "./type-create-form";
import { TypeViewPanel } from "./type-view";

export function App(props: {
  workspace: WorkspaceStore;
  auth: AuthStore;
}): ReactElement {
  const authState = useObservable(props.auth);
  const state = useObservable(props.workspace);

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

  const renderContent = (): ReactElement => {
    if (state.loading) {
      return <div className="empty-state">loading…</div>;
    }
    const tab = state.activeTab;
    if (tab === null) {
      return (
        <div className="empty-state">
          <p className="dim">Open a type or object from the sidebar.</p>
        </div>
      );
    }
    if (tab.kind === "create-type") {
      return (
        <div className="tab-content create-type-page">
          <TypeCreateForm workspace={props.workspace} />
        </div>
      );
    }
    if (tab.kind === "type") {
      const schema = state.types.find((view) => view.name === tab.name);
      if (schema === undefined) {
        return <div className="empty-state dim">Type is gone.</div>;
      }
      return <TypeViewPanel workspace={props.workspace} schema={schema} />;
    }
    const object = state.objects.find((view) => view.uuid === tab.uuid);
    if (object === undefined) {
      return <div className="empty-state dim">Object is gone.</div>;
    }
    return (
      <div className="tab-content">
        <ObjectEditor key={object.uuid} workspace={props.workspace} object={object} />
      </div>
    );
  };

  return (
    <div className="app">
      <Sidebar workspace={props.workspace} auth={props.auth} />
      <main className="main">
        <TabBar workspace={props.workspace} />
        {state.error !== null && <div className="error-banner">{state.error}</div>}
        {renderContent()}
      </main>
    </div>
  );
}
