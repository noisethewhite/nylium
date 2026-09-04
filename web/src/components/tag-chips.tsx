import type { ReactElement } from "react";
import type { TagView } from "../contracts";
import type { TagCandidate } from "../state/object-editor";
import { ObjectEditorStore } from "../state/object-editor";
import { useObservable } from "../state/use-observable";
import { FloatingMenu } from "./floating-menu";
import { NameSearch } from "./name-search";
import { ObjectLabels } from "./object-labels";
import { TypeIcon } from "./type-icon";

/** ADR-0005: derived tags rendered as chips directly under the object's
 * name. A chip is one (owner, prop) edge projected onto this object;
 * its color is the owner type's color. Writes are member-side patches
 * of the owner's Array<T> prop — the server recomputes the projection. */
export function TagChips(props: { editor: ObjectEditorStore }): ReactElement {
  const state = useObservable(props.editor);
  return (
    <div className="tag-chips">
      {state.object.tags.map((tag, index) => (
        <TagChip
          key={`${tag.owner_uuid}:${tag.prop_key}:${index}`}
          tag={tag}
          onRemove={() => void props.editor.removeTag(tag)}
        />
      ))}
      <FloatingMenu
        wrapperClassName="tag-chip-add-menu"
        triggerClassName="tag-chip tag-chip-add"
        menuClassName="ref-picker-menu"
        title="Add tag"
        trigger={<>+ tag</>}
      >
        {(close) => (
          <NameSearch<TagCandidate>
            items={props.editor.tagCandidates()}
            getKey={(candidate) => `${candidate.owner.uuid}:${candidate.propKey}`}
            getLabel={(candidate) =>
              `${ObjectLabels.of(candidate.owner)} → ${candidate.propKey}`
            }
            renderIcon={(candidate) => {
              const view = props.editor.typeOf(candidate.owner.type_name);
              return view === undefined ? null : (
                <TypeIcon icon={view.icon} color={view.color} size={15} />
              );
            }}
            placeholder="Owner → array prop…"
            emptyLabel="No objects with an array of this type"
            onPick={(candidate) => {
              close();
              void props.editor.addTag(candidate);
            }}
          />
        )}
      </FloatingMenu>
    </div>
  );
}

function TagChip(props: { tag: TagView; onRemove: () => void }): ReactElement {
  return (
    <span className="tag-chip">
      <span className="tag-chip-dot" style={{ backgroundColor: props.tag.color }} />
      <span className="tag-chip-label">{props.tag.name}</span>
      <button className="tag-chip-remove" title="Remove tag" onClick={props.onRemove}>
        ×
      </button>
    </span>
  );
}
