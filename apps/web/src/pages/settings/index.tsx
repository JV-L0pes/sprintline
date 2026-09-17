import { useEffect, useRef, useState } from "react";
import { useOutletContext, useSearchParams } from "react-router-dom";
import { useMembers } from "@/entities/member/api";
import { useSession } from "@/entities/session";
import { JiraPanel } from "@/features/integrations/ui/jira-panel";
import { TrelloPanel } from "@/features/integrations/ui/trello-panel";
import { InviteDialog } from "@/features/members/ui/invite-dialog";
import type { Workspace } from "@/shared/api/types";
import { useI18n } from "@/shared/i18n";
import { formatDateFull } from "@/shared/lib/dates";
import { useReveal } from "@/shared/lib/use-reveal";
import { Button } from "@/shared/ui/button";
import { Avatar, Badge, EmptyState, Skeleton } from "@/shared/ui/misc";
import { useToast } from "@/shared/ui/toast";

export function SettingsPage() {
  const { t, language } = useI18n();
  const toast = useToast();
  const { user } = useSession();
  const { workspace } = useOutletContext<{ workspace: Workspace | undefined }>();
  const members = useMembers(workspace?.id);
  const [inviting, setInviting] = useState(false);
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
        {members.isLoading ? (
          <div className="grid gap-3">
            <Skeleton />
            <Skeleton />
          </div>
        ) : (members.data ?? []).length === 0 ? (
          <EmptyState title={t("members.title")} />
        ) : (
          <div className="led">
            {(members.data ?? []).map((member) => (
              <div key={member.user_id} className="led-row fade">
                <span className="flex items-center gap-3">
                  <Avatar name={member.name} />
                  <span className="grid gap-0.5">
                    <span className="font-semibold">
                      {member.name}
                      {member.user_id === user?.id ? " (voce)" : ""}
                    </span>
                    <span className="mono text-ash">{member.email}</span>
                  </span>
                </span>
                <span className="flex items-center gap-3">
                  <span className="mono text-ash">
                    {t("members.joinedAt")}{" "}
                    {formatDateFull(member.joined_at.slice(0, 10), language)}
                  </span>
                  <Badge tone={member.role === "OWNER" ? "live" : "neutral"}>
                    {t(`members.${member.role.toLowerCase()}`)}
                  </Badge>
                </span>
              </div>
            ))}
          </div>
        )}
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
    </div>
  );
}
