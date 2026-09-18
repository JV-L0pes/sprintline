import { useEffect, useRef } from "react";
import { useOutletContext, useSearchParams } from "react-router-dom";
import { JiraPanel } from "@/features/integrations/ui/jira-panel";
import { TrelloPanel } from "@/features/integrations/ui/trello-panel";
import { GeneralSettings } from "@/features/workspace/ui/general-settings";
import type { Workspace } from "@/shared/api/types";
import { useI18n } from "@/shared/i18n";
import { useReveal } from "@/shared/lib/use-reveal";
import { Skeleton } from "@/shared/ui/misc";
import { useToast } from "@/shared/ui/toast";

export function SettingsPage() {
  const { t } = useI18n();
  const toast = useToast();
  const { workspace } = useOutletContext<{ workspace: Workspace | undefined }>();
  const [searchParams] = useSearchParams();
  const jiraStatus = searchParams.get("jira");
  const trelloStatus = searchParams.get("trello");
  const notified = useRef<string | null>(null);
  useReveal([workspace?.id]);

  useEffect(() => {
    const callbackStatus = jiraStatus ?? trelloStatus;
    if (notified.current === callbackStatus || !callbackStatus) {
      return;
    }
    notified.current = callbackStatus;
    if (callbackStatus === "connected") {
      toast.push(t("integrations.callbackConnected"));
    } else if (callbackStatus === "error") {
      toast.push(t("integrations.callbackError"), "error");
    }
  }, [jiraStatus, trelloStatus, t, toast]);

  if (!workspace) {
    return <Skeleton className="mt-8 h-40" />;
  }

  const canManage = workspace.role === "OWNER" || workspace.role === "ADMIN";

  return (
    <div className="grid gap-12">
      <section>
        <div className="sec-head fade">
          <div>
            <p className="kicker">{workspace.name}</p>
            <h1 className="text-4xl">{t("workspace.settings")}</h1>
          </div>
        </div>
        {canManage ? (
          <GeneralSettings workspace={workspace} />
        ) : (
          <p className="text-sm text-ash">{t("workspace.adminOnly")}</p>
        )}
      </section>
      {canManage ? (
        <div className="fade grid gap-12">
          <JiraPanel workspaceId={workspace.id} />
          <TrelloPanel workspaceId={workspace.id} workspaceSlug={workspace.slug} />
        </div>
      ) : null}
    </div>
  );
}
