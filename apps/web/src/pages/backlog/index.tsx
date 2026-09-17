import { Plus } from "lucide-react";
import { useState } from "react";
import { useOutletContext, useParams } from "react-router-dom";
import { useProjects } from "@/entities/project/api";
import { useSprints } from "@/entities/sprint/api";
import { useItems } from "@/entities/work-item/api";
import { ItemDialog } from "@/features/work-item/ui/item-dialog";
import type { WorkItem, Workspace } from "@/shared/api/types";
import { useI18n } from "@/shared/i18n";
import { useReveal } from "@/shared/lib/use-reveal";
import { Button } from "@/shared/ui/button";
import { Skeleton } from "@/shared/ui/misc";
import { BacklogLedger } from "@/widgets/backlog-ledger";
import { ProjectNav } from "@/widgets/project-nav";

export function BacklogPage() {
  const { t } = useI18n();
  const { key } = useParams<{ slug: string; key: string }>();
  const { workspace } = useOutletContext<{ workspace: Workspace | undefined }>();
  const projects = useProjects(workspace?.id);
  const project = projects.data?.find((item) => item.key === key);
  const items = useItems(workspace?.id, project?.id);
  const sprints = useSprints(workspace?.id, project?.id);
  const [dialog, setDialog] = useState<{ open: boolean; item: WorkItem | null }>({
    open: false,
    item: null,
  });
  useReveal([items.data]);

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
      <div className="flex flex-wrap items-center justify-between gap-4">
        <ProjectNav slug={workspace.slug} projectKey={project.key} />
        <Button
          onClick={() => {
            setDialog({ open: true, item: null });
          }}
        >
          <Plus size={15} aria-hidden /> {t("backlog.newItem")}
        </Button>
      </div>
      {items.isLoading || sprints.isLoading ? (
        <div className="grid gap-3">
          <Skeleton className="h-40" />
        </div>
      ) : (
        <BacklogLedger
          workspaceId={workspace.id}
          projectId={project.id}
          sprints={sprints.data ?? []}
          items={items.data ?? []}
          onOpenItem={(item) => {
            setDialog({ open: true, item });
          }}
        />
      )}
      <ItemDialog
        open={dialog.open}
        item={dialog.item}
        onClose={() => {
          setDialog({ open: false, item: null });
        }}
        workspaceId={workspace.id}
        projectId={project.id}
        sprints={sprints.data}
      />
    </div>
  );
}
