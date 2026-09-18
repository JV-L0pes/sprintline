import { useEffect, useState } from "react";
import { useDeleteWorkspace } from "@/entities/workspace/api";
import type { Workspace } from "@/shared/api/types";
import { useI18n } from "@/shared/i18n";
import { ConfirmDialog } from "@/shared/ui/dialog";
import { Field, Input } from "@/shared/ui/input";
import { useToast } from "@/shared/ui/toast";

interface DeleteWorkspaceDialogProps {
  workspace: Workspace | null;
  onClose: () => void;
}

export function DeleteWorkspaceDialog({ workspace, onClose }: DeleteWorkspaceDialogProps) {
  const { t } = useI18n();
  const toast = useToast();
  const deleteWorkspace = useDeleteWorkspace();
  const [typed, setTyped] = useState("");

  useEffect(() => {
    setTyped("");
  }, [workspace?.id]);

  const matches = workspace !== null && typed.trim() === workspace.name;

  return (
    <ConfirmDialog
      open={workspace !== null}
      onClose={onClose}
      onConfirm={() => {
        if (!workspace || !matches) {
          return;
        }
        void deleteWorkspace
          .mutateAsync(workspace.id)
          .then(() => {
            toast.push(t("workspace.deleted"));
            onClose();
          })
          .catch((error: unknown) => {
            toast.pushError(error);
          });
      }}
      title={t("workspace.deleteTitle")}
      description={t("workspace.deleteHint")}
      confirmLabel={t("common.delete")}
      pending={deleteWorkspace.isPending}
    >
      <Field
        label={t("workspace.deleteTypeName")}
        htmlFor="workspace-delete-confirm"
        hint={workspace?.name}
      >
        <Input
          id="workspace-delete-confirm"
          value={typed}
          onChange={(event) => {
            setTyped(event.target.value);
          }}
          autoComplete="off"
        />
      </Field>
    </ConfirmDialog>
  );
}
