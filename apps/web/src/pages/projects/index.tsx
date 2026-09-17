import { useState } from "react";
import { Link, useNavigate, useOutletContext } from "react-router-dom";
import { useProjects } from "@/entities/project/api";
import { CreateProjectDialog } from "@/features/project/ui/create-project-dialog";
import type { Workspace } from "@/shared/api/types";
import { useI18n } from "@/shared/i18n";
import { useReveal } from "@/shared/lib/use-reveal";
import { Button } from "@/shared/ui/button";
import { EmptyState, Skeleton } from "@/shared/ui/misc";

export function ProjectsPage() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const { workspace } = useOutletContext<{ workspace: Workspace | undefined }>();
  const projects = useProjects(workspace?.id);
  const [creating, setCreating] = useState(false);
  useReveal([projects.data]);

  return (
    <div className="grid gap-8">
      <div className="sec-head fade">
        <div>
          <p className="kicker">{workspace?.name}</p>
          <h1 className="text-4xl">{t("project.label")}s</h1>
        </div>
        <Button
          onClick={() => {
            setCreating(true);
          }}
        >
          {t("project.create")}
        </Button>
      </div>
      {projects.isLoading ? (
        <div className="grid gap-3">
          <Skeleton />
          <Skeleton />
        </div>
      ) : (projects.data ?? []).length === 0 ? (
        <div className="fade">
          <EmptyState title={t("project.empty")} hint={t("project.emptyHint")} />
        </div>
      ) : (
        <div className="led">
          {(projects.data ?? []).map((project) => (
            <Link
              key={project.id}
              to={`/w/${workspace?.slug ?? ""}/p/${project.key}/board`}
              className="led-row fade"
            >
              <span className="grid gap-1">
                <span className="text-lg font-extrabold tracking-tight">{project.name}</span>
                <span className="mono text-ash">
                  {project.key} · {t(`project.${project.mode.toLowerCase()}`)}
                </span>
              </span>
              <span className="mono text-ash">→</span>
            </Link>
          ))}
        </div>
      )}
      <CreateProjectDialog
        open={creating}
        onClose={() => {
          setCreating(false);
        }}
        workspaceId={workspace?.id ?? ""}
        onCreated={(key) => {
          void navigate(`/w/${workspace?.slug ?? ""}/p/${key}/board`);
        }}
      />
    </div>
  );
}
