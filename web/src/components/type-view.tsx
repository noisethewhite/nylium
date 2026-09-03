import type { DragEvent, ReactElement } from "react";
import { useEffect, useState } from "react";
import type { PropView, TypeView } from "../contracts";
import { TypeLabels } from "../contracts";
import { WorkspaceStore } from "../state/workspace";

/** Six-dot grip (2×3) — the affordance that a schema row is draggable. */
function PropGrip(): ReactElement {
  const dots: ReactElement[] = [];
  for (let row = 0; row < 3; row += 1) {
    for (let col = 0; col < 2; col += 1) {
      dots.push(<circle key={`${row}-${col}`} cx={3 + col * 5} cy={3 + row * 4} r={1.4} />);
    }
  }
  return (
    <svg className="prop-grip-icon" width="11" height="14" viewBox="0 0 11 14">
      {dots}
    </svg>
  );
}

export function TypeViewPanel(props: {
  workspace: WorkspaceStore;
  schema: TypeView;
}): ReactElement {
  const { workspace, schema } = props;
  // optimistic order while a drop is in flight; server answer resets it
  const [order, setOrder] = useState<readonly PropView[]>(schema.props);
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [overIndex, setOverIndex] = useState<number | null>(null);

  useEffect(() => {
    setOrder(schema.props);
  }, [schema.props]);

  const dropAt = (target: number): void => {
    const moved = dragIndex === null ? undefined : order[dragIndex];
    if (moved === undefined || dragIndex === null || dragIndex === target) {
      return;
    }
    // the pinned `name` prop never leaves position 0
    if (order[0]?.key === "name" && (dragIndex === 0 || target === 0)) {
      return;
    }
    const next = order.filter((_, position) => position !== dragIndex);
    next.splice(target, 0, moved);
    setOrder(next);
    void workspace.reorderProps(
      schema.name,
      next.map((prop) => prop.key),
    );
  };

  const onDrop = (event: DragEvent, target: number): void => {
    event.preventDefault();
    dropAt(target);
    setDragIndex(null);
    setOverIndex(null);
  };

  const rowClass = (index: number): string => {
    const classes = ["schema-prop-row"];
    if (index === dragIndex) {
      classes.push("schema-prop-row-dragging");
    }
    if (index === overIndex && dragIndex !== null && dragIndex !== index) {
      classes.push("schema-prop-row-over");
    }
    return classes.join(" ");
  };

  return (
    <div className="tab-content">
      <div className="type-header">
        <h1>
          {schema.name}
          {schema.plural_name !== null && (
            <span className="type-plural dim">({schema.plural_name})</span>
          )}
        </h1>
        <button
          className="button button-danger"
          onClick={() => void workspace.deleteType(schema.name)}
        >
          Delete type
        </button>
      </div>
      <div className="schema-props">
        {order.map((prop, index) => {
          // the schema's first prop is the pinned `name` title — no grip,
          // not draggable, not a drop target
          const pinned = index === 0 && prop.key === "name";
          return (
            <div
              key={prop.key}
              className={rowClass(index)}
              draggable={!pinned}
              onDragStart={() => {
                if (!pinned) {
                  setDragIndex(index);
                }
              }}
              onDragOver={(event) => {
                if (pinned) {
                  return;
                }
                event.preventDefault();
                setOverIndex(index);
              }}
              onDragLeave={() => setOverIndex((current) => (current === index ? null : current))}
              onDrop={(event) => onDrop(event, index)}
              onDragEnd={() => {
                setDragIndex(null);
                setOverIndex(null);
              }}
            >
              {pinned ? (
                <span className="prop-grip prop-grip-spacer" title="The name prop is pinned first" />
              ) : (
                <span className="prop-grip" title="Drag to reorder">
                  <PropGrip />
                </span>
              )}
              <span className="schema-prop-key">{prop.key}</span>
              <span className="dim">{TypeLabels[prop.value_type] ?? prop.value_type}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
