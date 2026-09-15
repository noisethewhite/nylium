import type { DragEvent, ReactElement, ReactNode } from "react";
import { Fragment, useState } from "react";
import { WorkspaceStore } from "../state/workspace";
import { TypePicker } from "./type-picker";

/** Shared editor table: every row list in the editors (type/trait props,
 * enum options, unit parts, create-form drafts) is one Table instance
 * with typed columns. Column kinds: drag (grip to reorder), checkbox,
 * radio, string, type-selector, remove. Any column may carry a header
 * label — if at least one does, the table renders a header row. */

interface ColumnBase {
  readonly header?: string;
}

interface DragColumn extends ColumnBase {
  readonly kind: "drag";
}

interface CheckboxColumn<T> extends ColumnBase {
  readonly kind: "checkbox";
  readonly title?: string;
  readonly checked: (row: T) => boolean;
  readonly onToggle: (row: T, checked: boolean, index: number) => void;
  readonly visible?: (row: T, index: number) => boolean;
}

interface RadioColumn<T> extends ColumnBase {
  readonly kind: "radio";
  readonly name: string;
  readonly title?: string;
  readonly checked: (row: T) => boolean;
  readonly onSelect: (row: T, index: number) => void;
  readonly visible?: (row: T, index: number) => boolean;
}

interface StringColumn<T> extends ColumnBase {
  readonly kind: "string";
  readonly placeholder?: string;
  readonly numeric?: boolean;
  readonly value: (row: T) => string;
  /** locked rows render this instead of an input; the default static
   * rendering is the plain value text */
  readonly display?: (row: T, index: number) => ReactNode;
  readonly onEdit: (row: T, value: string, index: number) => void;
  readonly visible?: (row: T, index: number) => boolean;
}

interface TypeSelectorColumn<T> extends ColumnBase {
  readonly kind: "type-selector";
  readonly workspace: WorkspaceStore;
  readonly value: (row: T) => string;
  readonly display?: (row: T, index: number) => ReactNode;
  readonly onPick: (row: T, value: string, index: number) => void;
  readonly visible?: (row: T, index: number) => boolean;
}

interface RemoveColumn<T> extends ColumnBase {
  readonly kind: "remove";
  readonly title: string;
  readonly disabled?: (row: T, index: number, rows: readonly T[]) => boolean;
  readonly onRemove: (index: number) => void;
  readonly visible?: (row: T, index: number) => boolean;
}

export type TableColumn<T> =
  | DragColumn
  | CheckboxColumn<T>
  | RadioColumn<T>
  | StringColumn<T>
  | TypeSelectorColumn<T>
  | RemoveColumn<T>;

/** Six-dot grip (2×3) — the affordance that a row is draggable. */
function TableGrip(): ReactElement {
  const dots: ReactElement[] = [];
  for (let row = 0; row < 3; row += 1) {
    for (let col = 0; col < 2; col += 1) {
      dots.push(<circle key={`${row}-${col}`} cx={3 + col * 5} cy={3 + row * 4} r={1.4} />);
    }
  }
  return (
    <svg className="table-grip-icon" width="11" height="14" viewBox="0 0 11 14">
      {dots}
    </svg>
  );
}

export function Table<T>(props: {
  readonly rows: readonly T[];
  readonly columns: readonly TableColumn<T>[];
  readonly keyOf: (row: T, index: number) => string;
  /** presence enables drag-to-rearrange; locked rows never start a drag
   * and are never a drop target */
  readonly onReorder?: (from: number, to: number) => void;
  readonly locked?: (row: T, index: number) => boolean;
  /** extra content appended after the columns (function-bind button) */
  readonly rowExtra?: (row: T, index: number) => ReactNode;
  /** static rows rendered inside the table, after the editable rows
   * (trait-owned props on the type page) */
  readonly trailing?: ReactNode;
}): ReactElement {
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [overIndex, setOverIndex] = useState<number | null>(null);
  const isLocked = (row: T, index: number): boolean =>
    props.locked !== undefined && props.locked(row, index);
  const hasHeader = props.columns.some((column) => column.header !== undefined);

  const onDrop = (event: DragEvent, target: number): void => {
    event.preventDefault();
    if (
      props.onReorder === undefined ||
      dragIndex === null ||
      dragIndex === target
    ) {
      setDragIndex(null);
      setOverIndex(null);
      return;
    }
    props.onReorder(dragIndex, target);
    setDragIndex(null);
    setOverIndex(null);
  };

  const rowClass = (index: number): string => {
    const classes = ["table-row"];
    if (index === dragIndex) {
      classes.push("table-row-dragging");
    }
    if (index === overIndex && dragIndex !== null && dragIndex !== index) {
      classes.push("table-row-over");
    }
    return classes.join(" ");
  };

  const renderCell = (column: TableColumn<T>, row: T, index: number): ReactNode => {
    const locked = isLocked(row, index);
    switch (column.kind) {
      case "drag":
        // the grip column keeps its slot even on locked rows so the
        // string cells line up across the whole table
        if (locked || props.onReorder === undefined) {
          return <span className="table-grip table-grip-spacer" />;
        }
        return (
          <span className="table-grip" title="Drag to reorder">
            <TableGrip />
          </span>
        );
      case "checkbox":
        if (column.visible !== undefined && !column.visible(row, index)) {
          return null;
        }
        return (
          <input
            type="checkbox"
            title={column.title}
            checked={column.checked(row)}
            onChange={(event) => column.onToggle(row, event.target.checked, index)}
          />
        );
      case "radio":
        if (column.visible !== undefined && !column.visible(row, index)) {
          return null;
        }
        return (
          <input
            type="radio"
            name={column.name}
            title={column.title}
            checked={column.checked(row)}
            onChange={() => column.onSelect(row, index)}
          />
        );
      case "string": {
        if (column.visible !== undefined && !column.visible(row, index)) {
          return null;
        }
        const custom = column.display?.(row, index);
        if (locked && custom === undefined) {
          return <span className="table-cell-static">{column.value(row)}</span>;
        }
        if (custom !== undefined && custom !== null) {
          return custom;
        }
        return (
          <input
            className="input table-cell-string"
            placeholder={column.placeholder}
            inputMode={column.numeric === true ? "decimal" : undefined}
            value={column.value(row)}
            onChange={(event) => column.onEdit(row, event.target.value, index)}
          />
        );
      }
      case "type-selector": {
        if (column.visible !== undefined && !column.visible(row, index)) {
          return null;
        }
        const custom = column.display?.(row, index);
        if (locked && custom === undefined) {
          return <span className="dim">{column.value(row)}</span>;
        }
        if (custom !== undefined && custom !== null) {
          return custom;
        }
        return (
          <TypePicker
            workspace={column.workspace}
            value={column.value(row)}
            onChange={(value) => column.onPick(row, value, index)}
          />
        );
      }
      case "remove":
        if (column.visible !== undefined && !column.visible(row, index)) {
          return null;
        }
        return (
          <button
            className="icon-button"
            title={column.title}
            disabled={column.disabled?.(row, index, props.rows) ?? false}
            onClick={() => column.onRemove(index)}
          >
            ×
          </button>
        );
    }
  };

  return (
    <div className="table">
      {hasHeader && (
        <div className="table-header dim">
          {props.columns.map((column, position) => (
            <span
              key={position}
              className={
                column.kind === "string" ? "table-header-cell table-cell-string" : "table-header-cell"
              }
            >
              {column.header ?? ""}
            </span>
          ))}
        </div>
      )}
      {props.rows.map((row, index) => {
        const locked = isLocked(row, index);
        return (
          <div
            key={props.keyOf(row, index)}
            className={rowClass(index)}
            draggable={props.onReorder !== undefined && !locked}
            onDragStart={() => {
              if (props.onReorder !== undefined && !locked) {
                setDragIndex(index);
              }
            }}
            onDragOver={(event) => {
              if (props.onReorder === undefined || locked || dragIndex === null) {
                return;
              }
              event.preventDefault();
              setOverIndex(index);
            }}
            onDragLeave={() => setOverIndex((current) => (current === index ? null : current))}
            onDrop={(event) => {
              if (props.onReorder !== undefined && !locked) {
                onDrop(event, index);
              }
            }}
            onDragEnd={() => {
              setDragIndex(null);
              setOverIndex(null);
            }}
          >
            {props.columns.map((column, position) => (
              <Fragment key={position}>{renderCell(column, row, index)}</Fragment>
            ))}
            {props.rowExtra?.(row, index)}
          </div>
        );
      })}
      {props.trailing}
    </div>
  );
}
