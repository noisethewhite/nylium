import type { ReactElement } from "react";
import { useEffect, useState } from "react";
import { TypeNames } from "../contracts";
import { AuthStore } from "../state/auth";
import { ErrorStore } from "../state/errors";
import { useObservable } from "../state/use-observable";
import { WorkspaceStore } from "../state/workspace";
import { ErrorCenter } from "./error-center";
import { EnumCreateForm } from "./enum-create-form";
import { EnumTypePanel } from "./enum-type-view";
import { FileTypePanel } from "./file-type-view";
import { FunctionEditor } from "./function-editor";
import { LoginView } from "./login-view";
import { CalendarView } from "./calendar-view";
import { ObjectEditor } from "./object-editor";
import { ScalarTypePanel } from "./scalar-type-view";
import { Sidebar } from "./sidebar";
import { TabBar } from "./tab-bar";
import { TypeCreateForm } from "./type-create-form";
import { TypeViewPanel } from "./type-view";
import { UnitCreateForm } from "./unit-create-form";
import { UnitTypePanel } from "./unit-type-view";

export function App(props: {
  workspace: WorkspaceStore;
  auth: AuthStore;
  errors: ErrorStore;
}): ReactElement {
  const authState = useObservable(props.auth);
  const state = useObservable(props.workspace);
  // Mobile-only drawer state; on desktop the class this drives is
  // overridden by static layout, so the flag is inert there.
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    if (authState.status === "authenticated") {
      void props.workspace.init();
    }
  }, [authState.status, props.workspace]);

  // Cmd+S / Ctrl+S pins the active preview tab even when the form is
  // pristine — the save half of the VS Code preview-tab rule. The editor
  // mounts its own useSaveShortcut for the actual write; this one is
  // purely the tab-pinning concern and fires regardless of dirty state.
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent): void => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "s") {
        event.preventDefault();
        props.workspace.pinActiveTab();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [props.workspace]);

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
    if (tab.kind === "create-enum") {
      return (
        <div className="tab-content create-type-page">
          <EnumCreateForm workspace={props.workspace} />
        </div>
      );
    }
    if (tab.kind === "create-unit") {
      return (
        <div className="tab-content create-type-page">
          <UnitCreateForm workspace={props.workspace} />
        </div>
      );
    }
    if (tab.kind === "create-function") {
      return (
        <div className="tab-content create-type-page">
          <FunctionEditor workspace={props.workspace} />
        </div>
      );
    }
    if (tab.kind === "calendar") {
      return (
        <div className="tab-content">
          <CalendarView workspace={props.workspace} />
        </div>
      );
    }
    if (tab.kind === "function") {
      const fn = state.functions.find((view) => view.uuid === tab.uuid);
      if (fn === undefined) {
        return <div className="empty-state dim">Function is gone.</div>;
      }
      return (
        <div className="tab-content">
          <FunctionEditor key={fn.uuid} workspace={props.workspace} uuid={fn.uuid} />
        </div>
      );
    }
    if (tab.kind === "type") {
      const schema = state.types.find((view) => view.name === tab.name);
      if (schema === undefined) {
        return <div className="empty-state dim">Type is gone.</div>;
      }
      if (schema.kind === "enum") {
        return <EnumTypePanel key={tab.name} workspace={props.workspace} schema={schema} />;
      }
      if (schema.kind === "unit") {
        return <UnitTypePanel key={tab.name} workspace={props.workspace} schema={schema} />;
      }
      if (schema.kind === "file") {
        return <FileTypePanel key={tab.name} workspace={props.workspace} schema={schema} />;
      }
      if (TypeNames.isScalar(schema.name)) {
        return <ScalarTypePanel key={tab.name} schema={schema} />;
      }
      return <TypeViewPanel key={tab.name} workspace={props.workspace} schema={schema} />;
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
    <div className={sidebarOpen ? "app sidebar-open" : "app"}>
      <Sidebar
        workspace={props.workspace}
        auth={props.auth}
        onNavigate={() => setSidebarOpen(false)}
      />
      {sidebarOpen && (
        <div
          className="sidebar-backdrop"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      <main className="main">
        <div className="mobile-topbar">
          <button
            className="icon-button"
            title="Menu"
            aria-label="Open menu"
            onClick={() => setSidebarOpen(true)}
          >
            <span className="material-symbols-outlined">menu</span>
          </button>
          <span className="brand">nylium</span>
        </div>
        <TabBar workspace={props.workspace} />
        {renderContent()}
      </main>
      <ErrorCenter errors={props.errors} />
    </div>
  );
}
