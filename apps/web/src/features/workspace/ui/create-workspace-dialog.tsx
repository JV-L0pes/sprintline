import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { z } from "zod";
import { useCreateWorkspace } from "@/entities/workspace/api";
import { useI18n } from "@/shared/i18n";
import { Button } from "@/shared/ui/button";
import { Dialog } from "@/shared/ui/dialog";
import { Field, Input } from "@/shared/ui/input";
import { useToast } from "@/shared/ui/toast";

const schema = z.object({
  name: z.string().min(1).max(120),
  timezone: z.string().min(1).max(64),
});

type WorkspaceValues = z.infer<typeof schema>;

export function CreateWorkspaceDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useI18n();
  const toast = useToast();
  const navigate = useNavigate();
  const createWorkspace = useCreateWorkspace();
  const form = useForm<WorkspaceValues>({
    resolver: zodResolver(schema),
    values: { name: "", timezone: "America/Sao_Paulo" },
  });

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      const workspace = await createWorkspace.mutateAsync(values);
      form.reset();
      onClose();
      await navigate(`/w/${workspace.slug}`);
    } catch (error) {
      toast.pushError(error);
    }
  });

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={t("workspace.createTitle")}
      footer={
        <>
          <button type="button" className="plain" onClick={onClose}>
            {t("common.cancel")}
          </button>
          <Button type="submit" form="workspace-form" disabled={createWorkspace.isPending}>
            {t("common.create")}
          </Button>
        </>
      }
    >
      <form
        id="workspace-form"
        onSubmit={(event) => void onSubmit(event)}
        className="grid gap-4"
        noValidate
      >
        <Field label={t("workspace.name")} htmlFor="workspace-name">
          <Input id="workspace-name" {...form.register("name")} />
        </Field>
        <Field
          label={t("workspace.timezone")}
          htmlFor="workspace-timezone"
          hint="America/Sao_Paulo"
        >
          <Input id="workspace-timezone" {...form.register("timezone")} />
        </Field>
      </form>
    </Dialog>
  );
}
