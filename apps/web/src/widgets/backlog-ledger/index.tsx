import {
  DndContext,
  type DragEndEvent,
  KeyboardSensor,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import { GripVertical } from "lucide-react";
import { useState } from "react";
import { sortSprints } from "@/entities/sprint/model";
import { useAssignItemToSprint } from "@/entities/work-item/api";
import { typeLabelKey } from "@/entities/work-item/model";
import type { Sprint, WorkItem } from "@/shared/api/types";
import { useI18n } from "@/shared/i18n";
import { cn } from "@/shared/lib/cn";
import { Badge, EmptyState } from "@/shared/ui/misc";
import { useToast } from "@/shared/ui/toast";

function DroppableSection({
  id,
  title,
  meta,
  children,
}: {
  id: string;
  title: string;
  meta?: string;
  children: React.ReactNode;
}) {
  const { setNodeRef, isOver } = useDroppable({ id });
  return (
    <section ref={setNodeRef} className={cn("mb-6", isOver && "bg-hover")}>
      <div className="sec-head">
        <h3 className="text-xl">{title}</h3>
        {meta ? <span className="mono text-ash">{meta}</span> : null}
      </div>
      <div className="led">{children}</div>
    </section>
  );
}

function ItemRow({ item, onOpen }: { item: WorkItem; onOpen?: (item: WorkItem) => void }) {
  const { t } = useI18n();
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: item.id,
  });
  return (
    <div
      ref={setNodeRef}
      className={cn("led-row bg-paper", isDragging && "opacity-60")}
      style={
        transform
          ? {
              transform: `translate3d(${String(transform.x)}px, ${String(transform.y)}px, 0)`,
              zIndex: 10,
              position: "relative",
            }
          : undefined
      }
    >
      <span className="flex min-w-0 items-center gap-2">
        <button
          type="button"
          className="grip"
          aria-label={t("backlog.dragHandle")}
          {...attributes}
          {...listeners}
        >
          <GripVertical size={13} aria-hidden />
        </button>
        <button
          type="button"
          className="grid min-w-0 gap-1 text-left"
          onClick={() => onOpen?.(item)}
        >
          <span className="flex items-center gap-2">
            <span className="type-tag">{t(typeLabelKey(item.type))}</span>
            <span className="key">{item.key}</span>
            {item.done_at ? <span className="mono text-gold">DONE</span> : null}
          </span>
          <span className="text-sm font-semibold">{item.title}</span>
        </button>
      </span>
      <span className="mono text-ash">
        {item.story_points === null ? t("item.noEstimate") : `${String(item.story_points)} pts`}
      </span>
    </div>
  );
}

export function BacklogLedger({
  workspaceId,
  projectId,
  sprints,
  items,
  onOpenItem,
}: {
  workspaceId: string;
  projectId: string;
  sprints: Sprint[];
  items: WorkItem[];
  onOpenItem?: (item: WorkItem) => void;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const assign = useAssignItemToSprint(workspaceId, projectId);
  const [dragging, setDragging] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor),
  );

  function itemsOf(sprintId: string | null) {
    return items
      .filter((item) => item.sprint_id === sprintId)
      .sort((a, b) => a.position - b.position);
  }

  function onDragEnd(event: DragEndEvent) {
    setDragging(false);
    const itemId = String(event.active.id);
    if (!event.over) {
      return;
    }
    const overId = String(event.over.id);
    const sprintId =
      overId === "backlog"
        ? null
        : overId.startsWith("sprint:")
          ? overId.slice("sprint:".length)
          : undefined;
    if (sprintId === undefined) {
      return;
    }
    const item = items.find((candidate) => candidate.id === itemId);
    if (!item || item.sprint_id === sprintId) {
      return;
    }
    assign.mutate(
      { itemId, sprintId },
      {
        onError: (error) => {
          toast.pushError(error);
        },
      },
    );
  }

  const ordered = sortSprints(sprints);
  const planned = ordered.filter((sprint) => sprint.state === "PLANNED");
  const active = ordered.filter((sprint) => sprint.state === "ACTIVE");
  const completed = ordered.filter((sprint) => sprint.state === "COMPLETED").reverse();

  return (
    <DndContext
      sensors={sensors}
      onDragStart={() => {
        setDragging(true);
      }}
      onDragEnd={onDragEnd}
      onDragCancel={() => {
        setDragging(false);
      }}
    >
      <p className="mono mb-6 text-ash">{t("backlog.dragHint")}</p>
      {[...active, ...planned].map((sprint) => (
        <DroppableSection
          key={sprint.id}
          id={`sprint:${sprint.id}`}
          title={sprint.name}
          meta={`${t(`sprint.${sprint.state.toLowerCase()}`)} · ${String(itemsOf(sprint.id).length)}`}
        >
          {itemsOf(sprint.id).length === 0 ? (
            <p className="py-4 text-sm text-ash">{dragging ? "→" : t("sprint.empty")}</p>
          ) : (
            itemsOf(sprint.id).map((item) => (
              <ItemRow key={item.id} item={item} onOpen={onOpenItem} />
            ))
          )}
        </DroppableSection>
      ))}
      <DroppableSection
        id="backlog"
        title={t("backlog.product")}
        meta={String(itemsOf(null).length)}
      >
        {itemsOf(null).length === 0 ? (
          <EmptyState title={t("backlog.unplanned")} hint={t("backlog.dragHint")} />
        ) : (
          itemsOf(null).map((item) => <ItemRow key={item.id} item={item} onOpen={onOpenItem} />)
        )}
      </DroppableSection>
      {completed.length > 0 ? (
        <section className="mb-6">
          <div className="sec-head">
            <h3 className="text-xl">{t("sprint.completed")}</h3>
            <Badge>{completed.length}</Badge>
          </div>
          {completed.map((sprint) => (
            <details key={sprint.id} className="border-b border-rule py-3">
              <summary className="cursor-pointer text-sm font-semibold">{sprint.name}</summary>
              <div className="led mt-2">
                {itemsOf(sprint.id).map((item) => (
                  <ItemRow key={item.id} item={item} onOpen={onOpenItem} />
                ))}
              </div>
            </details>
          ))}
        </section>
      ) : null}
    </DndContext>
  );
}
