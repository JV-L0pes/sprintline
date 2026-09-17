import {
  type Announcements,
  closestCorners,
  DndContext,
  type DragEndEvent,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  useDroppable,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useMemo, useState } from "react";
import { useMoveItem } from "@/entities/work-item/api";
import { typeLabelKey } from "@/entities/work-item/model";
import type { Board, BoardColumn, WorkItem } from "@/shared/api/types";
import { useI18n } from "@/shared/i18n";
import { cn } from "@/shared/lib/cn";
import { useToast } from "@/shared/ui/toast";

function Card({ item, onOpen }: { item: WorkItem; onOpen?: (item: WorkItem) => void }) {
  const { t } = useI18n();
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: item.id,
  });
  return (
    <article
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={cn("card", isDragging && "dragging")}
    >
      <button
        type="button"
        className="grid gap-2 text-left"
        aria-label={`${item.key}: ${item.title}`}
        onClick={() => onOpen?.(item)}
        {...attributes}
        {...listeners}
      >
        <span className="flex items-center justify-between gap-2">
          <span className="type-tag">{t(typeLabelKey(item.type))}</span>
          <span className="key">{item.key}</span>
        </span>
        <span className="title">{item.title}</span>
        <span className="meta">
          <span className="mono text-ash">
            {item.story_points === null ? t("item.noEstimate") : `${String(item.story_points)} pts`}
          </span>
          {item.done_at ? <span className="mono text-gold">DONE</span> : null}
        </span>
      </button>
    </article>
  );
}

function Column({
  column,
  items,
  onOpenItem,
}: {
  column: BoardColumn;
  items: WorkItem[];
  onOpenItem?: (item: WorkItem) => void;
}) {
  const { t } = useI18n();
  const { setNodeRef, isOver } = useDroppable({ id: `column:${column.id}` });
  const overLimit = column.wip_limit !== null && items.length >= column.wip_limit;
  return (
    <section className={cn("col", isOver && "over")} aria-label={column.name}>
      <header className="col-head">
        <h3 className="mono">{column.name}</h3>
        <span className={cn("col-count", overLimit && "over")}>
          {items.length}
          {column.wip_limit !== null ? `/${String(column.wip_limit)}` : ""}
          {overLimit ? ` · ${t("board.wip")}` : ""}
        </span>
      </header>
      <div ref={setNodeRef} className="col-body">
        <SortableContext
          items={items.map((item) => item.id)}
          strategy={verticalListSortingStrategy}
        >
          {items.map((item) => (
            <Card key={item.id} item={item} onOpen={onOpenItem} />
          ))}
        </SortableContext>
      </div>
    </section>
  );
}

export function KanbanBoard({
  workspaceId,
  projectId,
  board,
  onOpenItem,
}: {
  workspaceId: string;
  projectId: string;
  board: Board;
  onOpenItem?: (item: WorkItem) => void;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const moveItem = useMoveItem(workspaceId, projectId);
  const [activeId, setActiveId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const byColumnId = useMemo(() => {
    const grouped = new Map<string, WorkItem[]>();
    for (const column of board.columns) {
      grouped.set(
        column.id,
        board.items
          .filter((item) => item.status_column_id === column.id)
          .sort((a, b) => a.position - b.position),
      );
    }
    return grouped;
  }, [board]);

  const columnById = useMemo(
    () => new Map(board.columns.map((column) => [column.id, column])),
    [board.columns],
  );

  const activeItem = board.items.find((item) => item.id === activeId);

  function labelForDroppable(overId: string): string {
    if (overId.startsWith("column:")) {
      return columnById.get(overId.slice("column:".length))?.name ?? "";
    }
    const item = board.items.find((candidate) => candidate.id === overId);
    if (!item) {
      return "";
    }
    return columnById.get(item.status_column_id)?.name ?? "";
  }

  const announcements: Announcements = {
    onDragStart: ({ active }) =>
      t("board.pickUp", { title: board.items.find((item) => item.id === active.id)?.title ?? "" }),
    onDragOver: ({ over }) =>
      over ? t("board.moveTo", { column: labelForDroppable(String(over.id)) }) : undefined,
    onDragEnd: ({ over }) =>
      t("board.drop", { column: over ? labelForDroppable(String(over.id)) : "" }),
    onDragCancel: () => undefined,
  };

  function resolveTarget(overId: string, movingId: string) {
    if (overId.startsWith("column:")) {
      const columnId = overId.slice("column:".length);
      const column = columnById.get(columnId);
      if (!column) {
        return undefined;
      }
      const items = (byColumnId.get(columnId) ?? []).filter((item) => item.id !== movingId);
      return { column, index: items.length };
    }
    const overItem = board.items.find((item) => item.id === overId);
    if (!overItem) {
      return undefined;
    }
    const column = columnById.get(overItem.status_column_id);
    if (!column) {
      return undefined;
    }
    const items = (byColumnId.get(column.id) ?? []).filter((item) => item.id !== movingId);
    return { column, index: items.findIndex((item) => item.id === overId) };
  }

  function onDragEnd(event: DragEndEvent) {
    setActiveId(null);
    const movingId = String(event.active.id);
    if (!event.over) {
      return;
    }
    const target = resolveTarget(String(event.over.id), movingId);
    const item = board.items.find((candidate) => candidate.id === movingId);
    if (!target || !item) {
      return;
    }
    const currentItems = byColumnId.get(item.status_column_id) ?? [];
    const currentIndex = currentItems.findIndex((candidate) => candidate.id === movingId);
    if (item.status_column_id === target.column.id && currentIndex === target.index) {
      return;
    }
    moveItem.mutate(
      { itemId: movingId, columnId: target.column.id, index: target.index },
      {
        onSuccess: (result) => {
          if (result.wip_warning) {
            toast.push(t("board.wipWarning"));
          }
        },
        onError: (error) => {
          toast.pushError(error);
        },
      },
    );
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      accessibility={{ announcements }}
      onDragStart={(event) => {
        setActiveId(String(event.active.id));
      }}
      onDragEnd={onDragEnd}
      onDragCancel={() => {
        setActiveId(null);
      }}
    >
      <div className="board">
        {[...board.columns]
          .sort((a, b) => a.position - b.position)
          .map((column) => (
            <Column
              key={column.id}
              column={column}
              items={byColumnId.get(column.id) ?? []}
              onOpenItem={onOpenItem}
            />
          ))}
      </div>
      <DragOverlay>
        {activeItem ? (
          <div className="card dragging" style={{ width: "16rem" }}>
            <span className="key">{activeItem.key}</span>
            <span className="title block">{activeItem.title}</span>
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}
