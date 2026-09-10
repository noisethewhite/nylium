import type { ReactElement } from "react";
import { useEffect, useState } from "react";
import type { StorageView } from "../contracts";
import { WorkspaceStore } from "../state/workspace";
import { FloatingMenu } from "./floating-menu";

function formatBytes(bytes: number): string {
  if (bytes >= 1024 * 1024 * 1024) {
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
  }
  if (bytes >= 1024 * 1024) {
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }
  return `${(bytes / 1024).toFixed(1)} KB`;
}

function formatPct(part: number, total: number): string {
  const pct = (part / total) * 100;
  return `${pct < 1 && pct > 0 ? pct.toFixed(2) : pct.toFixed(1)}%`;
}

/** Sidebar-footer popover: free space on the data volume and nylium's
 * own share of it. Fetches fresh every time it opens. */
export function StorageMenu(props: {
  workspace: WorkspaceStore;
}): ReactElement {
  return (
    <FloatingMenu
      wrapperClassName="storage-menu-wrap"
      triggerClassName="icon-button"
      menuClassName="type-menu storage-menu"
      title="Storage"
      trigger={
        <span className="material-symbols-outlined" style={{ fontSize: 15 }}>
          database
        </span>
      }
    >
      {() => <StorageStats workspace={props.workspace} />}
    </FloatingMenu>
  );
}

function StorageStats(props: { workspace: WorkspaceStore }): ReactElement {
  const [stats, setStats] = useState<StorageView | null>(null);
  useEffect(() => {
    let stale = false;
    void props.workspace.storageStats().then((view) => {
      if (!stale) setStats(view);
    });
    return () => {
      stale = true;
    };
  }, [props.workspace]);
  if (stats === null) {
    return <div className="storage-menu-row dim">Loading…</div>;
  }
  return (
    <div className="storage-menu-body">
      <div className="storage-menu-row">
        <span className="dim">Free</span>
        <span>
          {formatBytes(stats.free_bytes)}
          <span className="dim"> of {formatBytes(stats.total_bytes)}</span>
        </span>
      </div>
      <div className="storage-menu-row">
        <span className="dim">Free %</span>
        <span>{formatPct(stats.free_bytes, stats.total_bytes)}</span>
      </div>
      <div className="storage-menu-row">
        <span className="dim">nylium</span>
        <span>
          {formatBytes(stats.nylium_bytes)}
          <span className="dim"> ({formatPct(stats.nylium_bytes, stats.total_bytes)})</span>
        </span>
      </div>
    </div>
  );
}
