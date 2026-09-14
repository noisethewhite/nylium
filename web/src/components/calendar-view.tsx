import type { ReactElement } from "react";
import { useMemo, useState } from "react";
import { MONTH_NAMES } from "../month-names";
import { useObservable } from "../state/use-observable";
import type { WorkspaceStore } from "../state/workspace";
import { CalendarGrid } from "./calendar-logic";
import type { DayKey } from "./calendar-logic";
import { ObjectLabels } from "./object-labels";
import { TypeIcon } from "./type-icon";

/** ADR-0009 (section 2): a thin renderer for the generic month grid. All
 * date/span/cell math lives in CalendarGrid (calendar-logic.ts); this
 * component only holds cursor/selection state and paints the result. */

export function CalendarView(props: { workspace: WorkspaceStore }): ReactElement {
  const state = useObservable(props.workspace);
  const [cursor, setCursor] = useState<{ year: number; month: number }>(() => {
    const now = new Date();
    return { year: now.getFullYear(), month: now.getMonth() };
  });
  const [selectedDay, setSelectedDay] = useState<DayKey | null>(null);

  const todayKey = useMemo(() => {
    const now = new Date();
    return CalendarGrid.dayKeyFromParts(now.getFullYear(), now.getMonth(), now.getDate());
  }, []);

  const byDay = useMemo(
    () => CalendarGrid.entriesByDay(state.objects, state.types),
    [state.objects, state.types],
  );

  const prevMonth = (): void => {
    setCursor((current) =>
      current.month === 0
        ? { year: current.year - 1, month: 11 }
        : { ...current, month: current.month - 1 },
    );
  };

  const nextMonth = (): void => {
    setCursor((current) =>
      current.month === 11
        ? { year: current.year + 1, month: 0 }
        : { ...current, month: current.month + 1 },
    );
  };

  const goToday = (): void => {
    const now = new Date();
    setCursor({ year: now.getFullYear(), month: now.getMonth() });
    setSelectedDay(todayKey);
  };

  const cells = CalendarGrid.buildCells(cursor.year, cursor.month);
  const selectedEntries = selectedDay === null ? [] : (byDay.get(selectedDay) ?? []);
  const sortedEntries = CalendarGrid.sortEntries(selectedEntries);

  return (
    <div className="calendar-view">
      <div className="calendar-header">
        <div className="calendar-nav">
          <button className="icon-button" title="Previous month" onClick={prevMonth}>
            ←
          </button>
          <span className="calendar-title">
            {MONTH_NAMES[cursor.month]} {cursor.year}
          </span>
          <button className="icon-button" title="Next month" onClick={nextMonth}>
            →
          </button>
        </div>
        <button className="button" onClick={goToday}>
          Today
        </button>
      </div>
      <div className="calendar-grid" role="grid">
        {CalendarGrid.WEEKDAY_LABELS.map((label) => (
          <div className="calendar-weekday" key={label}>
            {label}
          </div>
        ))}
        {cells.map((cell) => {
          const isToday = cell.dayKey !== null && cell.dayKey === todayKey;
          const isSelected = cell.dayKey !== null && cell.dayKey === selectedDay;
          const count = cell.dayKey === null ? 0 : (byDay.get(cell.dayKey)?.length ?? 0);
          const className = [
            "calendar-cell",
            isToday ? "calendar-cell-today" : "",
            isSelected ? "calendar-cell-selected" : "",
          ]
            .filter(Boolean)
            .join(" ");
          return (
            <button
              key={cell.key}
              className={className}
              disabled={cell.dayKey === null}
              onClick={() => cell.dayKey !== null && setSelectedDay(cell.dayKey)}
            >
              <span className="calendar-cell-day">{cell.day ?? ""}</span>
              {count > 0 && <span className="calendar-cell-badge">{count}</span>}
            </button>
          );
        })}
      </div>
      <div className="calendar-day-detail">
        {selectedDay === null ? (
          <p className="dim">Select a day to see the objects dated on it.</p>
        ) : (
          <>
            <div className="calendar-day-title">{CalendarGrid.friendlyDay(selectedDay)}</div>
            {sortedEntries.length === 0 ? (
              <p className="dim">Nothing dated on this day.</p>
            ) : (
              sortedEntries.map((entry, index) => {
                const type = state.types.find((candidate) => candidate.name === entry.typeName);
                const label = CalendarGrid.spanLabel(entry.span);
                return (
                  <button
                    key={`${entry.object.uuid}-${entry.span.start}-${index}`}
                    className="calendar-event-row"
                    onClick={() => props.workspace.openObject(entry.object.uuid)}
                  >
                    {type !== undefined && <TypeIcon icon={type.icon} color={type.color} size={14} />}
                    <span className="calendar-event-label">{ObjectLabels.of(entry.object)}</span>
                    <span className="dim">{entry.typeName}</span>
                    {label !== "" && <span className="calendar-event-span dim">{label}</span>}
                  </button>
                );
              })
            )}
          </>
        )}
      </div>
    </div>
  );
}
