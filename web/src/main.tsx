import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./components/app";
import { WhiteoutApi } from "./net/whiteout-api";
import { WorkspaceStore } from "./state/workspace";
import "./styles/tokens.css";
import "./styles/app.css";

/** Composition root: build the object graph, kick off loading, render. */
const container = document.getElementById("root");
if (container === null) {
  throw new Error("root element missing");
}
const api = new WhiteoutApi();
const workspace = new WorkspaceStore(api);
void workspace.init();

createRoot(container).render(
  <StrictMode>
    <App workspace={workspace} />
  </StrictMode>,
);
