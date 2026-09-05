import { useState } from "react";
import type { ReactElement } from "react";
import type { FileView, TypeView } from "../contracts";
import { NyliumApi } from "../net/nylium-api";
import { useObservable } from "../state/use-observable";
import { WorkspaceStore } from "../state/workspace";
import { TypeIcon } from "./type-icon";

/** Read-only panel for the built-in File/Document/Image types. The type
 * itself is immutable (lock marker); the files uploaded under it are
 * first-class rows (ADR-0008) that can be renamed, downloaded or
 * deleted here. */
export function FileTypePanel(props: {
  workspace: WorkspaceStore;
  schema: TypeView;
}): ReactElement {
  const state = useObservable(props.workspace);
  const files = state.files.filter((file) => file.type_name === props.schema.name);

  return (
    <div className="tab-content">
      <div className="type-actions-bar">
        <span className="dim type-header-title">
          <Lock /> Built-in file type
        </span>
      </div>
      <div className="type-header-boxes">
        <div className="type-field-box">
          <span className="type-field-box-label">Type name</span>
          <div className="type-field-box-content">
            <TypeIcon icon={props.schema.icon} color={props.schema.color} size={22} />
            <span className="type-name-input">{props.schema.name}</span>
          </div>
        </div>
      </div>
      <p className="dim type-file-note">
        A {props.schema.name} prop holds an uploaded file. Files are created by
        upload (sidebar “+”), and each one can be renamed, downloaded or
        deleted below — but the type itself cannot be edited.
      </p>
      {files.length === 0 ? (
        <div className="type-menu-empty dim">No {props.schema.name} files yet.</div>
      ) : (
        <div className="type-menu-list">
          {files.map((file) => (
            <FileRow key={file.uuid} file={file} workspace={props.workspace} />
          ))}
        </div>
      )}
    </div>
  );
}

/** One uploaded file: download link + size, inline rename, delete. */
function FileRow(props: {
  file: FileView;
  workspace: WorkspaceStore;
}): ReactElement {
  const { file, workspace } = props;
  const [editing, setEditing] = useState(false);
  const [nameDraft, setNameDraft] = useState(file.name);

  if (editing) {
    return (
      <div className="type-menu-row file-row">
        <input
          className="input"
          value={nameDraft}
          onChange={(event) => setNameDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              void workspace.renameFile(file.uuid, nameDraft.trim());
              setEditing(false);
            }
            if (event.key === "Escape") {
              setEditing(false);
              setNameDraft(file.name);
            }
          }}
          autoFocus
        />
        <button
          className="button button-primary"
          onClick={() => {
            void workspace.renameFile(file.uuid, nameDraft.trim());
            setEditing(false);
          }}
        >
          Save
        </button>
        <button
          className="icon-button"
          title="Cancel"
          onClick={() => {
            setEditing(false);
            setNameDraft(file.name);
          }}
        >
          ×
        </button>
      </div>
    );
  }

  return (
    <div className="type-menu-row file-row">
      <a
        className="type-row-name"
        href={NyliumApi.fileUrl(file.uuid)}
        target="_blank"
        rel="noreferrer"
        title="Download"
      >
        {file.name}
      </a>
      <span className="dim">{formatBytes(file.size_bytes)}</span>
      <button className="icon-button" title="Rename" onClick={() => setEditing(true)}>
        ✎
      </button>
      <button
        className="icon-button"
        title="Delete file"
        onClick={() => void workspace.deleteFile(file.uuid)}
      >
        ×
      </button>
    </div>
  );
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** Material lock glyph — the "immutable builtin" marker. */
export function Lock(): ReactElement {
  return (
    <span className="material-symbols-outlined lock-marker" aria-hidden>
      lock
    </span>
  );
}
