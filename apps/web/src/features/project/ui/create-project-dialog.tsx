import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import { useCreateProject, useProjects } from "@/entities/project/api";
import { suggestProjectKey } from "@/features/project/model";
import { useI18n } from "@/shared/i18n";
import { Button } from "@/shared/ui/button";
import { Dialog } from "@/shared/ui/dialog";
import { Field, Input } from "@/shared/ui/input";
import { Select } from "@/shared/ui/select";
import { useToast } from "@/shared/ui/toast";

const schema = z.object({
  name: z.string().min(1).max(120),
  mode: z.enum(["POINTS", "COUNT"]),
});

type ProjectValues = z.infer<typeof schema>;

export function CreateProjectDialog({
  open,
  onClose,
  workspaceId,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  workspaceId: string;
  onCreated?: (key: string) => void;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const createProject = useCreateProject(workspaceId);
  const projects = useProjects(workspaceId);
  const form = useForm<ProjectValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", mode: "POINTS" },
  });

  const onSubmit = form.handleSubmit(async (values) => {
    const taken = new Set((projects.data ?? []).map((project) => project.key));
    try {
      const project = await createProject.mutateAsync({
        ...values,
        key: suggestProjectKey(values.name, taken),
      });
      form.reset();
      onClose();
      onCreated?.(project.key);
    } catch (error) {
      toast.pushError(error);
    }
  });

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={t("project.createTitle")}
      footer={
        <>
          <button type="button" className="plain" onClick={onClose}>
            {t("common.cancel")}
          </button>
          <Button type="submit" form="project-form" disabled={createProject.isPending}>
            {t("common.create")}
          </Button>
        </>
      }
    >
      <form
        id="project-form"
        onSubmit={(event) => void onSubmit(event)}
        className="grid gap-4"
        noValidate
      >
        <Field label={t("project.name")} htmlFor="project-name">
          <Input id="project-name" {...form.register("name")} />
        </Field>
        <Field label={t("item.points")} htmlFor="project-mode">
          <Controller
            control={form.control}
            name="mode"
            render={({ field }) => (
              <Select
                id="project-mode"
                value={field.value}
                onChange={(event) => {
                  field.onChange(event.target.value);
                }}
                onBlur={field.onBlur}
              >
                <option value="POINTS">{t("project.points")}</option>
                <option value="COUNT">{t("project.count")}</option>
              </Select>
            )}
          />
        </Field>
      </form>
    </Dialog>
  );
}
