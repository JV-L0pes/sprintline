import { zodResolver } from "@hookform/resolvers/zod";
import { useMemo } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { useUpdateWorkspace } from "@/entities/workspace/api";
import { detectTimezone, timezoneOptions } from "@/features/workspace/model";
import type { Workspace } from "@/shared/api/types";
import { useI18n } from "@/shared/i18n";
import { Button } from "@/shared/ui/button";
import { Field, Input, Select } from "@/shared/ui/input";
import { useToast } from "@/shared/ui/toast";

const schema = z.object({
  name: z.string().min(1).max(120),
  timezone: z.string().min(1).max(64),
});

type GeneralValues = z.infer<typeof schema>;

export function GeneralSettings({ workspace }: { workspace: Workspace }) {
  const { t } = useI18n();
  const toast = useToast();
  const detected = useMemo(detectTimezone, []);
  const timezoneChoices = useMemo(() => timezoneOptions(detected), [detected]);
  const updateWorkspace = useUpdateWorkspace(workspace.id);
  const form = useForm<GeneralValues>({
    resolver: zodResolver(schema),
    values: { name: workspace.name, timezone: workspace.timezone },
  });

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      await updateWorkspace.mutateAsync(values);
      toast.push(t("workspace.updated"));
    } catch (error) {
      toast.pushError(error);
    }
  });

  return (
    <form
      id="workspace-general-form"
      onSubmit={(event) => void onSubmit(event)}
      className="grid max-w-xl gap-4"
      noValidate
    >
      <Field label={t("workspace.name")} htmlFor="workspace-general-name">
        <Input id="workspace-general-name" {...form.register("name")} />
      </Field>
      <Field
        label={t("workspace.timezone")}
        htmlFor="workspace-general-timezone"
        hint={t("workspace.timezoneHint")}
      >
        <Select id="workspace-general-timezone" {...form.register("timezone")}>
          {timezoneChoices.map(([value, label]) => (
            <option key={value} value={value}>
              {value === label ? value : `${label} — ${value}`}
            </option>
          ))}
        </Select>
      </Field>
      <div className="flex items-center justify-between gap-3">
        <p className="mono text-ash">{workspace.slug}</p>
        <Button type="submit" disabled={updateWorkspace.isPending}>
          {t("common.save")}
        </Button>
      </div>
    </form>
  );
}
