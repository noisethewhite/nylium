import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./components/app";
import { AuthApi } from "./net/auth-api";
import { NyliumApi } from "./net/nylium-api";
import { AuthStore } from "./state/auth";
import { ErrorStore } from "./state/errors";
import { WorkspaceStore } from "./state/workspace";
import "./styles/tokens.css";
import "./styles/app.css";

/** Composition root: build the object graph, probe the session, render. */
const container = document.getElementById("root");
if (container === null) {
  throw new Error("root element missing");
}
const errors = new ErrorStore();
const reportApiError = (error: Error): void => errors.report(error.message);
const auth = new AuthStore(new AuthApi(reportApiError));
const workspace = new WorkspaceStore(new NyliumApi(reportApiError), () =>
  auth.expire(),
);

// JS crashes and stray rejections join the same log as API errors
window.addEventListener("error", (event) => errors.report(event.message));
window.addEventListener("unhandledrejection", (event) => {
  const reason: unknown = event.reason;
  errors.report(reason instanceof Error ? reason.message : String(reason));
});

void auth.init();

createRoot(container).render(
  <StrictMode>
    <App workspace={workspace} auth={auth} errors={errors} />
  </StrictMode>,
);
