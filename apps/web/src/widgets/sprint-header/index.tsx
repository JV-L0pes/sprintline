import {
  activeSprint,
  plannedSprints,
  progressPercentage,
  sortSprints,
  sprintStateLabelKey,
} from "@/entities/sprint/model";
import { SprintActions } from "@/features/sprint/ui/sprint-dialogs";
import type { Sprint } from "@/shared/api/types";
import { useI18n } from "@/shared/i18n";
import { daysRemaining, formatDateFull, toIsoDate } from "@/shared/lib/dates";
import { Badge, EmptyState, LiveDot, Meter } from "@/shared/ui/misc";

export function SprintHeader({
  workspaceId,
  projectId,
  sprints,
}: {
  workspaceId: string;
  projectId: string;
  sprints: Sprint[];
}) {
  const { t, language } = useI18n();
  const planned = plannedSprints(sprints);
  const sprint = activeSprint(sprints) ?? planned[0];

  if (!sprint) {
    return (
      <section className="fade on mb-8">
        <div className="sec-head">
          <div>
            <p className="kicker">{t("sprint.title")}</p>
            <h1 className="text-3xl">{t("sprint.noActive")}</h1>
          </div>
        </div>
        {sortSprints(sprints).length === 0 ? (
          <EmptyState title={t("sprint.empty")} hint={t("sprint.emptyHint")} />
        ) : null}
      </section>
    );
  }

  const remaining = daysRemaining(sprint.end_date, toIsoDate(new Date()));
  const percentage = progressPercentage(sprint);
  const nextSprint = planned.find((candidate) => candidate.id !== sprint.id);

  return (
    <section className="fade on mb-8">
      <div className="sec-head">
        <div className="grid gap-2">
          <p className="kicker flex items-center gap-2">
            {sprint.state === "ACTIVE" ? <LiveDot /> : <LiveDot muted />}
            {t(sprintStateLabelKey(sprint.state))}
          </p>
          <h1 className="text-3xl md:text-4xl">{sprint.name}</h1>
          <p className="lede">{sprint.goal ?? "—"}</p>
          <p className="mono text-ash">
            {formatDateFull(sprint.start_date, language)} —{" "}
            {formatDateFull(sprint.end_date, language)} ·{" "}
            {t("sprint.daysLeft", { days: remaining })}
          </p>
        </div>
        <div className="flex flex-col items-end gap-3">
          <Badge tone={sprint.state === "ACTIVE" ? "live" : "neutral"}>
            {sprint.done_points}/{sprint.total_points} pts
          </Badge>
          <SprintActions
            workspaceId={workspaceId}
            projectId={projectId}
            sprint={sprint}
            nextSprint={nextSprint}
          />
        </div>
      </div>
      <Meter value={percentage} max={100} gold={percentage >= 100} />
    </section>
  );
}
