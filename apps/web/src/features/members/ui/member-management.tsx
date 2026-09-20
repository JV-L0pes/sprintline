import { KeyRound, Trash2 } from "lucide-react";
import { useState } from "react";
import {
  useMembers,
  useRemoveMember,
  useResetMemberPassword,
  useUpdateMemberRole,
} from "@/entities/member/api";
import { useSession } from "@/entities/session";
import { useChangeOwnPassword } from "@/features/auth/api";
import type { Member, Role } from "@/shared/api/types";
import { useI18n } from "@/shared/i18n";
import { formatDateFull } from "@/shared/lib/dates";
import { Button } from "@/shared/ui/button";
import { ConfirmDialog, Dialog } from "@/shared/ui/dialog";
import { Field, Input } from "@/shared/ui/input";
import { Avatar, Badge, EmptyState, Skeleton } from "@/shared/ui/misc";
import { Select } from "@/shared/ui/select";
import { useToast } from "@/shared/ui/toast";

const ROLE_RANK: Record<Role, number> = { OWNER: 3, ADMIN: 2, MEMBER: 1, VIEWER: 0 };
const MANAGEABLE_ROLES: Role[] = ["VIEWER", "MEMBER", "ADMIN", "OWNER"];

function ResetPasswordDialog({
  workspaceId,
  member,
  open,
  onClose,
}: {
  workspaceId: string;
  member: Member | null;
  open: boolean;
  onClose: () => void;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const reset = useResetMemberPassword(workspaceId);
  const [password, setPassword] = useState("");

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={t("members.resetPasswordTitle", { name: member?.name ?? "" })}
      footer={
        <>
          <button type="button" className="plain" onClick={onClose}>
            {t("common.cancel")}
          </button>
          <Button
            disabled={reset.isPending || password.length < 10}
            onClick={() => {
              if (!member) {
                return;
              }
              reset.mutate(
                { userId: member.user_id, newPassword: password },
                {
                  onSuccess: () => {
                    toast.push(t("members.resetPasswordDone"));
                    setPassword("");
                    onClose();
                  },
                  onError: (error) => {
                    toast.pushError(error);
                  },
                },
              );
            }}
          >
            {t("members.resetPassword")}
          </Button>
        </>
      }
    >
      <p className="text-sm text-ash">{t("members.resetPasswordHint")}</p>
      <Field label={t("auth.newPassword")} htmlFor="reset-password" hint={t("auth.passwordHint")}>
        <Input
          id="reset-password"
          type="text"
          value={password}
          onChange={(event) => {
            setPassword(event.target.value);
          }}
        />
      </Field>
    </Dialog>
  );
}

export function MemberManagement({
  workspaceId,
  actorRole,
}: {
  workspaceId: string;
  actorRole: Role;
}) {
  const { t, language } = useI18n();
  const toast = useToast();
  const { user } = useSession();
  const members = useMembers(workspaceId);
  const updateRole = useUpdateMemberRole(workspaceId);
  const removeMember = useRemoveMember(workspaceId);
  const [removing, setRemoving] = useState<Member | null>(null);
  const [resetting, setResetting] = useState<Member | null>(null);

  const canManage = (member: Member) =>
    ROLE_RANK[actorRole] > ROLE_RANK[member.role] && member.user_id !== user?.id;

  if (members.isLoading) {
    return (
      <div className="grid gap-3">
        <Skeleton />
        <Skeleton />
      </div>
    );
  }
  if ((members.data ?? []).length === 0) {
    return <EmptyState title={t("members.title")} />;
  }

  return (
    <>
      <div className="led">
        {(members.data ?? []).map((member) => {
          const manageable = canManage(member);
          return (
            <div key={member.user_id} className="led-row fade">
              <span className="flex items-center gap-3">
                <Avatar name={member.name} />
                <span className="grid gap-0.5">
                  <span className="font-semibold">
                    {member.name}
                    {member.user_id === user?.id ? " (você)" : ""}
                  </span>
                  <span className="mono text-ash">{member.email}</span>
                </span>
              </span>
              <span className="flex flex-wrap items-center justify-end gap-3">
                <span className="mono text-ash">
                  {t("members.joinedAt")} {formatDateFull(member.joined_at.slice(0, 10), language)}
                </span>
                {manageable ? (
                  <>
                    <div className="w-32 shrink-0">
                      <Select
                        aria-label={t("members.role")}
                        value={member.role}
                        disabled={updateRole.isPending}
                        onChange={(event) => {
                          updateRole.mutate(
                            { userId: member.user_id, role: event.target.value },
                            {
                              onError: (error) => {
                                toast.pushError(error);
                              },
                            },
                          );
                        }}
                      >
                        {MANAGEABLE_ROLES.filter(
                          (role) => ROLE_RANK[role] <= ROLE_RANK[actorRole],
                        ).map((role) => (
                          <option key={role} value={role}>
                            {t(`members.${role.toLowerCase()}`)}
                          </option>
                        ))}
                      </Select>
                    </div>
                    <button
                      type="button"
                      className="sq"
                      aria-label={t("members.resetPassword")}
                      onClick={() => {
                        setResetting(member);
                      }}
                    >
                      <KeyRound size={14} strokeWidth={2} aria-hidden />
                    </button>
                    <button
                      type="button"
                      className="sq"
                      aria-label={t("members.remove")}
                      onClick={() => {
                        setRemoving(member);
                      }}
                    >
                      <Trash2 size={14} strokeWidth={2} aria-hidden />
                    </button>
                  </>
                ) : (
                  <Badge tone={member.role === "OWNER" ? "live" : "neutral"}>
                    {t(`members.${member.role.toLowerCase()}`)}
                  </Badge>
                )}
              </span>
            </div>
          );
        })}
      </div>
      <ConfirmDialog
        open={removing !== null}
        onClose={() => {
          setRemoving(null);
        }}
        onConfirm={() => {
          if (!removing) {
            return;
          }
          removeMember.mutate(removing.user_id, {
            onSuccess: () => {
              setRemoving(null);
            },
            onError: (error) => {
              toast.pushError(error);
            },
          });
        }}
        title={t("members.removeTitle")}
        description={t("members.removeHint")}
        confirmLabel={t("members.remove")}
        pending={removeMember.isPending}
      />
      <ResetPasswordDialog
        workspaceId={workspaceId}
        member={resetting}
        open={resetting !== null}
        onClose={() => {
          setResetting(null);
        }}
      />
    </>
  );
}

export function ChangePasswordDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useI18n();
  const toast = useToast();
  const change = useChangeOwnPassword();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={t("auth.changePassword")}
      footer={
        <>
          <button type="button" className="plain" onClick={onClose}>
            {t("common.cancel")}
          </button>
          <Button
            disabled={change.isPending || next.length < 10 || current.length === 0}
            onClick={() => {
              change.mutate(
                { currentPassword: current, newPassword: next },
                {
                  onSuccess: () => {
                    toast.push(t("auth.passwordChanged"));
                    setCurrent("");
                    setNext("");
                    onClose();
                  },
                  onError: (error) => {
                    toast.pushError(error);
                  },
                },
              );
            }}
          >
            {t("common.save")}
          </Button>
        </>
      }
    >
      <p className="text-sm text-ash">{t("auth.changePasswordHint")}</p>
      <Field label={t("auth.currentPassword")} htmlFor="current-password">
        <Input
          id="current-password"
          type="password"
          autoComplete="current-password"
          value={current}
          onChange={(event) => {
            setCurrent(event.target.value);
          }}
        />
      </Field>
      <Field label={t("auth.newPassword")} htmlFor="new-password" hint={t("auth.passwordHint")}>
        <Input
          id="new-password"
          type="password"
          autoComplete="new-password"
          value={next}
          onChange={(event) => {
            setNext(event.target.value);
          }}
        />
      </Field>
    </Dialog>
  );
}
