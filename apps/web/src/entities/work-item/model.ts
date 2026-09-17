import type { Priority, WorkItem, WorkItemType } from "@/shared/api/types";

export const WORK_ITEM_TYPES: WorkItemType[] = ["EPIC", "STORY", "TASK", "BUG", "SUBTASK"];

export const PRIORITIES: Priority[] = ["LOWEST", "LOW", "MEDIUM", "HIGH", "HIGHEST"];

const TYPE_LABEL: Record<WorkItemType, string> = {
  EPIC: "item.epic",
  STORY: "item.story",
  TASK: "item.task",
  BUG: "item.bug",
  SUBTASK: "item.subtask",
};

const PRIORITY_LABEL: Record<Priority, string> = {
  LOWEST: "item.lowest",
  LOW: "item.low",
  MEDIUM: "item.medium",
  HIGH: "item.high",
  HIGHEST: "item.highest",
};

export function typeLabelKey(type: WorkItemType): string {
  return TYPE_LABEL[type];
}

export function priorityLabelKey(priority: Priority): string {
  return PRIORITY_LABEL[priority];
}

export function isDone(item: WorkItem): boolean {
  return item.done_at !== null;
}

export function sortByPosition(items: WorkItem[]): WorkItem[] {
  return [...items].sort((a, b) => a.position - b.position);
}

export function itemsForSprint(items: WorkItem[], sprintId: string | null): WorkItem[] {
  return items.filter((item) => item.sprint_id === sprintId);
}

export function backlogItems(items: WorkItem[], sprintIds: Set<string>): WorkItem[] {
  return items.filter((item) => item.sprint_id === null || !sprintIds.has(item.sprint_id));
}

export function pointsSum(items: WorkItem[]): number {
  return items.reduce((total, item) => total + (item.story_points ?? 0), 0);
}

export function unestimatedCount(items: WorkItem[]): number {
  return items.filter((item) => item.type !== "SUBTASK" && item.story_points === null).length;
}
