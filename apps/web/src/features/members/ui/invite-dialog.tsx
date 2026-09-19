import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import { useInviteMember } from "@/entities/member/api";
import { useI18n } from "@/shared/i18n";
import { Button } from "@/shared/ui/button";
import { Dialog } from "@/shared/ui/dialog";
import { Field, Input } from "@/shared/ui/input";
import { Select } from "@/shared/ui/select";
import { useToast } from "@/shared/ui/toast";

const schema = z.object({
  email: z.string().email(),
  role: z.enum(["ADMIN", "MEMBER", "VIEWER"]),
});

type InviteValues = z.infer<typeof schema>;

export function InviteDialog({
  open,
  onClose,
  workspaceId,
}: {
  open: boolean;
  onClose: () => void;
  workspaceId: string;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const invite = useInviteMember(workspaceId);
  const [link, setLink] = useState<string | null>(null);
  const form = useForm<InviteValues>({
    resolver: zodResolver(schema),
    values: { email: "", role: "MEMBER" },
  });

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      const result = await invite.mutateAsync(values);
      setLink(`${window.location.origin}/invite/${result.token}`);
    } catch (error) {
      toast.pushError(error);
    }
  });

  return (
    <Dialog
      open={open}
      onClose={() => {
        setLink(null);
        onClose();
      }}
      title={t("members.inviteTitle")}
      footer={
        <>
          <button
            type="button"
            className="plain"
            onClick={() => {
              setLink(null);
              onClose();
            }}
          >
            {t("common.close")}
          </button>
          {!link ? (
            <Button type="submit" form="invite-form" disabled={invite.isPending}>
              {t("members.invite")}
            </Button>
          ) : null}
        </>
      }
    >
      {link ? (
        <div className="grid gap-3">
          <p className="text-sm text-ash">{t("members.inviteHint")}</p>
          <div className="flex items-center gap-3">
            <Input readOnly value={link} aria-label={t("members.inviteLink")} />
            <Button
              variant="outline"
              onClick={() => {
                void navigator.clipboard.writeText(link).then(() => {
                  toast.push(t("common.copied"));
                });
              }}
            >
              {t("common.copy")}
            </Button>
          </div>
        </div>
      ) : (
        <form
          id="invite-form"
          onSubmit={(event) => void onSubmit(event)}
          className="grid gap-4"
          noValidate
        >
          <Field label={t("auth.email")} htmlFor="invite-email">
            <Input id="invite-email" type="email" {...form.register("email")} />
          </Field>
          <Field label={t("members.role")} htmlFor="invite-role">
            <Controller
              control={form.control}
              name="role"
              render={({ field }) => (
                <Select
                  id="invite-role"
                  value={field.value}
                  onChange={(event) => {
                    field.onChange(event.target.value);
                  }}
                  onBlur={field.onBlur}
                >
                  <option value="MEMBER">{t("members.member")}</option>
                  <option value="ADMIN">{t("members.admin")}</option>
                  <option value="VIEWER">{t("members.viewer")}</option>
                </Select>
              )}
            />
          </Field>
        </form>
      )}
    </Dialog>
  );
}
