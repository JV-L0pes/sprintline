import { ArrowRight, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { useSession } from "@/entities/session";
import { useWorkspaces } from "@/entities/workspace/api";
import { LanguageSwitch } from "@/features/shell/ui/language-switch";
import { ThemeToggle } from "@/features/shell/ui/theme-toggle";
import { CreateWorkspaceDialog } from "@/features/workspace/ui/create-workspace-dialog";
import { DeleteWorkspaceDialog } from "@/features/workspace/ui/delete-workspace-dialog";
import type { Workspace } from "@/shared/api/types";
import { useI18n } from "@/shared/i18n";
import { useReveal } from "@/shared/lib/use-reveal";
import { Button } from "@/shared/ui/button";
import { EmptyState, Skeleton } from "@/shared/ui/misc";

export function HomePage() {
  const { t } = useI18n();
  const { user } = useSession();
  const workspaces = useWorkspaces();
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState<Workspace | null>(null);
  useReveal([workspaces.data]);

  return (
    <main className="shell min-h-screen pb-24">
      <header className="bar stuck">
        <div className="shell bar-in">
          <span className="mark" aria-hidden>
            S
          </span>
          <div className="flex-1">
            <p className="mono text-ash">{t("common.appName")}</p>
            <p className="text-sm font-bold">{user?.name}</p>
          </div>
          <LanguageSwitch />
          <ThemeToggle />
        </div>
      </header>
      <div className="pt-32">
        <div className="sec-head fade">
          <div>
            <p className="kicker">{t("workspace.label")}s</p>
            <h1 className="text-4xl">
              <span className="line">
                <span>{t("common.tagline")}</span>
              </span>
            </h1>
          </div>
          <Button
            onClick={() => {
              setCreating(true);
            }}
          >
            {t("workspace.create")}
          </Button>
        </div>
        {workspaces.isLoading ? (
          <div className="grid gap-3">
            <Skeleton />
            <Skeleton />
          </div>
        ) : (workspaces.data ?? []).length === 0 ? (
          <div className="fade">
            <EmptyState title={t("workspace.empty")} hint={t("workspace.emptyHint")} />
          </div>
        ) : (
          <div className="led">
            {(workspaces.data ?? []).map((workspace) => (
              <div key={workspace.id} className="led-row fade">
                <Link to={`/w/${workspace.slug}`} className="grid gap-1">
                  <span className="text-lg font-extrabold tracking-tight">{workspace.name}</span>
                  <span className="mono text-ash">
                    {workspace.timezone} · {t(`members.${workspace.role.toLowerCase()}`)}
                  </span>
                </Link>
                <div className="flex items-center gap-2">
                  <Link to={`/w/${workspace.slug}`} className="sq" aria-label={t("workspace.open")}>
                    <ArrowRight size={15} strokeWidth={2} aria-hidden />
                  </Link>
                  {workspace.role === "OWNER" ? (
                    <button
                      type="button"
                      className="sq"
                      aria-label={t("workspace.deleteTitle")}
                      onClick={() => {
                        setDeleting(workspace);
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
      </div>
      <CreateWorkspaceDialog
        open={creating}
        onClose={() => {
          setCreating(false);
        }}
      />
      <DeleteWorkspaceDialog
        workspace={deleting}
        onClose={() => {
          setDeleting(null);
        }}
      />
    </main>
  );
}
