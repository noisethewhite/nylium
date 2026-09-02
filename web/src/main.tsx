import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./components/app";
import { AuthApi } from "./net/auth-api";
import { NyliumApi } from "./net/nylium-api";
import { AuthStore } from "./state/auth";
import { WorkspaceStore } from "./state/workspace";
import "./styles/tokens.css";
import "./styles/app.css";

/** Composition root: build the object graph, probe the session, render. */
const container = document.getElementById("root");
if (container === null) {
  throw new Error("root element missing");
}
const auth = new AuthStore(new AuthApi());
const workspace = new WorkspaceStore(new NyliumApi(), () => auth.expire());
void auth.init();

createRoot(container).render(
  <StrictMode>
    <App workspace={workspace} auth={auth} />
  </StrictMode>,
);
