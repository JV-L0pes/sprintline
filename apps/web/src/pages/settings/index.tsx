import { useEffect, useRef, useState } from "react";
import { useOutletContext, useSearchParams } from "react-router-dom";
import { useMembers } from "@/entities/member/api";
import { JiraPanel } from "@/features/integrations/ui/jira-panel";
import { TrelloPanel } from "@/features/integrations/ui/trello-panel";
import { InviteDialog } from "@/features/members/ui/invite-dialog";
import { ChangePasswordDialog, MemberManagement } from "@/features/members/ui/member-management";
import type { Workspace } from "@/shared/api/types";
import { useI18n } from "@/shared/i18n";
import { useReveal } from "@/shared/lib/use-reveal";
import { Button } from "@/shared/ui/button";
import { Skeleton } from "@/shared/ui/misc";
import { useToast } from "@/shared/ui/toast";

export function SettingsPage() {
  const { t } = useI18n();
  const toast = useToast();
  const { workspace } = useOutletContext<{ workspace: Workspace | undefined }>();
  const members = useMembers(workspace?.id);
  const [inviting, setInviting] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);
  const [searchParams] = useSearchParams();
  const jiraStatus = searchParams.get("jira");
  const trelloStatus = searchParams.get("trello");
  const notified = useRef<string | null>(null);
  useReveal([members.data]);

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

  const canInvite = workspace.role === "OWNER" || workspace.role === "ADMIN";

  return (
    <div className="grid gap-12">
      <section>
        <div className="sec-head fade">
          <div>
            <p className="kicker">{workspace.name}</p>
            <h1 className="text-4xl">{t("members.title")}</h1>
          </div>
          <div className="flex gap-3">
            <Button
              variant="outline"
              onClick={() => {
                setChangingPassword(true);
              }}
            >
              {t("auth.changePassword")}
            </Button>
            {canInvite ? (
              <Button
                onClick={() => {
                  setInviting(true);
                }}
              >
                {t("members.invite")}
              </Button>
            ) : null}
          </div>
        </div>
        <MemberManagement workspaceId={workspace.id} actorRole={workspace.role} />
      </section>
      {canInvite ? (
        <div className="fade grid gap-12">
          <JiraPanel workspaceId={workspace.id} />
          <TrelloPanel workspaceId={workspace.id} workspaceSlug={workspace.slug} />
        </div>
      ) : null}
      <InviteDialog
        open={inviting}
        onClose={() => {
          setInviting(false);
        }}
        workspaceId={workspace.id}
      />
      <ChangePasswordDialog
        open={changingPassword}
        onClose={() => {
          setChangingPassword(false);
        }}
      />
    </div>
  );
}
