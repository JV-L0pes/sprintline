import { useEffect, useState } from "react";
import { useOutletContext, useParams } from "react-router-dom";
import { useBurndown, useCfd, useFlowTimes, useVelocity } from "@/entities/metric/api";
import { useProjects } from "@/entities/project/api";
import { useSprints } from "@/entities/sprint/api";
import { defaultSprint, sortSprints } from "@/entities/sprint/model";
import type { Workspace } from "@/shared/api/types";
import { useI18n } from "@/shared/i18n";
import { useReveal } from "@/shared/lib/use-reveal";
import { EmptyState, Skeleton } from "@/shared/ui/misc";
import { Select } from "@/shared/ui/select";
import { BurndownPanel } from "@/widgets/burndown-panel";
import { CfdPanel } from "@/widgets/cfd-panel";
import { FlowPanel } from "@/widgets/flow-panel";
import { ProjectNav } from "@/widgets/project-nav";
import { VelocityPanel } from "@/widgets/velocity-panel";

export function MetricsPage() {
  const { t } = useI18n();
  const { key } = useParams<{ slug: string; key: string }>();
  const { workspace } = useOutletContext<{ workspace: Workspace | undefined }>();
  const projects = useProjects(workspace?.id);
  const project = projects.data?.find((item) => item.key === key);
  const sprints = useSprints(workspace?.id, project?.id);
  const [sprintId, setSprintId] = useState<string | undefined>(undefined);

  useEffect(() => {
    if (!sprintId && sprints.data && sprints.data.length > 0) {
      setSprintId(defaultSprint(sprints.data)?.id);
    }
  }, [sprintId, sprints.data]);

  const burndown = useBurndown(workspace?.id, sprintId);
  const cfd = useCfd(workspace?.id, sprintId);
  const velocity = useVelocity(workspace?.id, project?.id);
  const flow = useFlowTimes(workspace?.id, project?.id);
  useReveal([burndown.data]);

  if (!workspace || !project) {
    return (
      <div className="grid gap-3 pt-8">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-40" />
      </div>
    );
  }

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <ProjectNav slug={workspace.slug} projectKey={project.key} />
        <label className="field" htmlFor="sprint-select">
          <span className="lab">{t("metrics.selectSprint")}</span>
          <Select
            id="sprint-select"
            value={sprintId ?? ""}
            onChange={(event) => {
              setSprintId(event.target.value);
            }}
          >
            {(sprints.data ?? []).map((sprint) => (
              <option key={sprint.id} value={sprint.id}>
                {sprint.name} · {t(`sprint.${sprint.state.toLowerCase()}`)}
              </option>
            ))}
          </Select>
        </label>
      </div>
      {!sprintId || (sprints.data ?? []).length === 0 ? (
        <EmptyState title={t("metrics.empty")} hint={t("metrics.emptyHint")} />
      ) : burndown.isLoading ? (
        <Skeleton className="h-72" />
      ) : burndown.data ? (
        <div className="fade on">
          <BurndownPanel burndown={burndown.data} />
          {velocity.data ? <VelocityPanel velocity={velocity.data} /> : null}
          {cfd.data ? <CfdPanel cfd={cfd.data} /> : null}
          {flow.data ? <FlowPanel flow={flow.data} /> : null}
          <p className="mono text-ash">
            {sortSprints(sprints.data ?? []).length} {t("sprint.title").toLowerCase()}s ·{" "}
            {project.key}
          </p>
        </div>
      ) : (
        <EmptyState title={t("metrics.empty")} hint={t("metrics.emptyHint")} />
      )}
    </div>
  );
}
