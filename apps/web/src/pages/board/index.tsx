import { Plus } from "lucide-react";
import { useState } from "react";
import { useOutletContext, useParams } from "react-router-dom";
import { useBoard } from "@/entities/board/api";
import { useProjects } from "@/entities/project/api";
import { useSprints } from "@/entities/sprint/api";
import { sortSprints } from "@/entities/sprint/model";
import { ColumnsDialog } from "@/features/board-columns/ui/columns-dialog";
import { CreateSprintDialog } from "@/features/sprint/ui/sprint-dialogs";
import { ItemDialog } from "@/features/work-item/ui/item-dialog";
import type { WorkItem, Workspace } from "@/shared/api/types";
import { useI18n } from "@/shared/i18n";
import { useReveal } from "@/shared/lib/use-reveal";
import { Button } from "@/shared/ui/button";
import { EmptyState, Skeleton } from "@/shared/ui/misc";
import { KanbanBoard } from "@/widgets/kanban-board";
import { ProjectNav } from "@/widgets/project-nav";
import { SprintHeader } from "@/widgets/sprint-header";

export function BoardPage() {
  const { t } = useI18n();
  const { key } = useParams<{ slug: string; key: string }>();
  const { workspace } = useOutletContext<{ workspace: Workspace | undefined }>();
  const projects = useProjects(workspace?.id);
  const project = projects.data?.find((item) => item.key === key);
  const board = useBoard(workspace?.id, project?.id);
  const sprints = useSprints(workspace?.id, project?.id);
  const [itemDialog, setItemDialog] = useState<{ open: boolean; item: WorkItem | null }>({
    open: false,
    item: null,
  });
  const [sprintDialog, setSprintDialog] = useState(false);
  const [columnsDialog, setColumnsDialog] = useState(false);
  useReveal([board.data]);

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
      <SprintHeader
        workspaceId={workspace.id}
        projectId={project.id}
        sprints={sortSprints(sprints.data ?? [])}
      />
      <div className="flex flex-wrap items-center justify-between gap-4">
        <ProjectNav slug={workspace.slug} projectKey={project.key} />
        <div className="flex gap-3">
          <Button
            variant="outline"
            disabled={!board.data}
            onClick={() => {
              setColumnsDialog(true);
            }}
          >
            {t("board.columns")}
          </Button>
          <Button
            variant="outline"
            onClick={() => {
              setSprintDialog(true);
            }}
          >
            {t("sprint.create")}
          </Button>
          <Button
            onClick={() => {
              setItemDialog({ open: true, item: null });
            }}
          >
            <Plus size={15} aria-hidden /> {t("backlog.newItem")}
          </Button>
        </div>
      </div>
      {board.isLoading ? (
        <div className="grid gap-3">
          <Skeleton className="h-40" />
        </div>
      ) : board.data ? (
        <KanbanBoard
          workspaceId={workspace.id}
          projectId={project.id}
          board={board.data}
          onOpenItem={(item) => {
            setItemDialog({ open: true, item });
          }}
        />
      ) : (
        <EmptyState title={t("metrics.empty")} hint={t("metrics.emptyHint")} />
      )}
      <ItemDialog
        open={itemDialog.open}
        item={itemDialog.item}
        onClose={() => {
          setItemDialog({ open: false, item: null });
        }}
        workspaceId={workspace.id}
        projectId={project.id}
        sprints={sprints.data}
      />
      <CreateSprintDialog
        open={sprintDialog}
        onClose={() => {
          setSprintDialog(false);
        }}
        workspaceId={workspace.id}
        projectId={project.id}
      />
      {board.data ? (
        <ColumnsDialog
          open={columnsDialog}
          onClose={() => {
            setColumnsDialog(false);
          }}
          workspaceId={workspace.id}
          projectId={project.id}
          board={board.data}
        />
      ) : null}
    </div>
  );
}
