import { useEffect } from "react";
import type { WorkspaceStore } from "./workspace";

/** VS Code preview-tab rule, edit half: the first time an editor's draft
 * goes dirty, pin the active tab so a later sidebar click doesn't evict
 * it. Idempotent — re-pinning an already-pinned tab is a no-op. */
export function usePinTabOnEdit(workspace: WorkspaceStore, dirty: boolean): void {
  useEffect(() => {
    if (dirty) {
      workspace.pinActiveTab();
    }
  }, [dirty, workspace]);
}
