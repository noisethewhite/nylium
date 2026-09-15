import type { ReactElement } from "react";
import type { ObjectRef, ObjectView } from "../contracts";
import type { WorkspaceState, WorkspaceStore } from "../state/workspace";
import { useObservable } from "../state/use-observable";
import { ObjectLabels } from "./object-labels";
import { TypeIcon } from "./type-icon";

/** ADR-0020: backlinks — every object pointing at this one through a
 * link prop or array membership. Read-only: the projection is
 * recomputed server-side on every read, edits happen on the owner
 * side (the tag chips above cover the array case). Click opens the
 * referring object. Nothing renders when there are no referrers. */
export function BacklinkChips(props: {
  workspace: WorkspaceStore;
  object: ObjectView;
}): ReactElement | null {
  const state = useObservable(props.workspace);
  if (props.object.backlinks.length === 0) {
    return null;
  }
  return (
    <div className="object-editor-backlinks">
      <div className="computed-header dim">Backlinks</div>
      <div className="backlink-rows">
        {props.object.backlinks.map((ref) => (
          <BacklinkRow
            key={ref.uuid}
            reference={ref}
            state={state}
            onOpen={() => props.workspace.openObject(ref.uuid)}
          />
        ))}
      </div>
    </div>
  );
}

function BacklinkRow(props: {
  reference: ObjectRef;
  state: WorkspaceState;
  onOpen: () => void;
}): ReactElement {
  const owner = props.state.objects.find(
    (view) => view.uuid === props.reference.uuid,
  );
  const typeView = props.state.types.find(
    (view) => view.name === props.reference.type_name,
  );
  const label =
    owner !== undefined
      ? ObjectLabels.of(owner)
      : `${props.reference.type_name} · ${props.reference.uuid.slice(0, 8)}`;
  return (
    <button
      className="backlink-row"
      onClick={props.onOpen}
      title={`Open ${props.reference.type_name}`}
    >
      {typeView !== undefined && (
        <TypeIcon icon={typeView.icon} color={typeView.color} size={15} />
      )}
      <span className="backlink-label">{label}</span>
      <span className="backlink-type dim">{props.reference.type_name}</span>
    </button>
  );
}
