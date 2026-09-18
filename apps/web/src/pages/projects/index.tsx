import { ArrowRight, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useOutletContext } from "react-router-dom";
import { useArchiveProject, useProjects } from "@/entities/project/api";
import { CreateProjectDialog } from "@/features/project/ui/create-project-dialog";
import type { Project, Workspace } from "@/shared/api/types";
import { useI18n } from "@/shared/i18n";
import { useReveal } from "@/shared/lib/use-reveal";
import { Button } from "@/shared/ui/button";
import { ConfirmDialog } from "@/shared/ui/dialog";
import { EmptyState, Skeleton } from "@/shared/ui/misc";
import { useToast } from "@/shared/ui/toast";

export function ProjectsPage() {
  const { t } = useI18n();
  const toast = useToast();
  const navigate = useNavigate();
  const { workspace } = useOutletContext<{ workspace: Workspace | undefined }>();
  const projects = useProjects(workspace?.id);
  const archiveProject = useArchiveProject(workspace?.id ?? "");
  const [creating, setCreating] = useState(false);
  const [archiving, setArchiving] = useState<Project | null>(null);
  const canArchive = workspace?.role === "OWNER" || workspace?.role === "ADMIN";
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
            <div key={project.id} className="led-row fade">
              <Link
                to={`/w/${workspace?.slug ?? ""}/p/${project.key}/board`}
                className="grid gap-1"
              >
                <span className="text-lg font-extrabold tracking-tight">{project.name}</span>
                <span className="mono text-ash">
                  {project.key} · {t(`project.${project.mode.toLowerCase()}`)}
                </span>
              </Link>
              <div className="flex items-center gap-2">
                <Link
                  to={`/w/${workspace?.slug ?? ""}/p/${project.key}/board`}
                  className="sq"
                  aria-label={t("project.open")}
                >
                  <ArrowRight size={15} strokeWidth={2} aria-hidden />
                </Link>
                {canArchive ? (
                  <button
                    type="button"
                    className="sq"
                    aria-label={t("project.archiveTitle")}
                    onClick={() => {
                      setArchiving(project);
                    }}
                  >
                    <Trash2 size={15} strokeWidth={2} aria-hidden />
                  </button>
                ) : null}
              </div>
            </div>
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
      <ConfirmDialog
        open={archiving !== null}
        onClose={() => {
          setArchiving(null);
        }}
        onConfirm={() => {
          if (!archiving) {
            return;
          }
          void archiveProject
            .mutateAsync(archiving.id)
            .then(() => {
              toast.push(t("project.archived"));
              setArchiving(null);
            })
            .catch((error: unknown) => {
              toast.pushError(error);
            });
        }}
        title={t("project.archiveTitle")}
        description={t("project.archiveHint")}
        confirmLabel={t("common.archive")}
        pending={archiveProject.isPending}
      />
    </div>
  );
}
