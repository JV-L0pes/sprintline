import type { Sprint, SprintState } from "@/shared/api/types";

const STATE_LABEL: Record<SprintState, string> = {
  PLANNED: "sprint.planned",
  ACTIVE: "sprint.active",
  COMPLETED: "sprint.completed",
};

export function sprintStateLabelKey(state: SprintState): string {
  return STATE_LABEL[state];
}

export function sortSprints(sprints: Sprint[]): Sprint[] {
  return [...sprints].sort((a, b) => a.start_date.localeCompare(b.start_date));
}

export function activeSprint(sprints: Sprint[]): Sprint | undefined {
  return sprints.find((sprint) => sprint.state === "ACTIVE");
}

export function plannedSprints(sprints: Sprint[]): Sprint[] {
  return sortSprints(sprints).filter((sprint) => sprint.state === "PLANNED");
}

export function completedSprints(sprints: Sprint[]): Sprint[] {
  return sortSprints(sprints)
    .filter((sprint) => sprint.state === "COMPLETED")
    .reverse();
}

/** Sprint inicial da pagina de métricas: ativa > última concluída > planejada. */
export function defaultSprint(sprints: Sprint[]): Sprint | undefined {
  return (
    activeSprint(sprints) ??
    completedSprints(sprints)[0] ??
    plannedSprints(sprints)[0] ??
    sortSprints(sprints)[0]
  );
}

export function progressPercentage(sprint: Sprint): number {
  if (sprint.total_points > 0) {
    return Math.min(100, Math.round((sprint.done_points / sprint.total_points) * 100));
  }
  if (sprint.total_items > 0) {
    return Math.min(100, Math.round((sprint.done_items / sprint.total_items) * 100));
  }
  return 0;
}
