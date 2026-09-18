import { useState } from "react";
import { useOutletContext } from "react-router-dom";
import { useMembers } from "@/entities/member/api";
import { InviteDialog } from "@/features/members/ui/invite-dialog";
import { ChangePasswordDialog, MemberManagement } from "@/features/members/ui/member-management";
import type { Workspace } from "@/shared/api/types";
import { useI18n } from "@/shared/i18n";
import { useReveal } from "@/shared/lib/use-reveal";
import { Button } from "@/shared/ui/button";
import { Skeleton } from "@/shared/ui/misc";

export function MembersPage() {
  const { t } = useI18n();
  const { workspace } = useOutletContext<{ workspace: Workspace | undefined }>();
  const members = useMembers(workspace?.id);
  const [inviting, setInviting] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);
  useReveal([members.data]);

  if (!workspace) {
    return <Skeleton className="mt-8 h-40" />;
  }

  const canInvite = workspace.role === "OWNER" || workspace.role === "ADMIN";

  return (
    <div>
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
