import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { useCompleteSprint, useCreateSprint, useStartSprint } from "@/entities/sprint/api";
import type { Sprint } from "@/shared/api/types";
import { useI18n } from "@/shared/i18n";
import { addDays, isValidSprintRange, toIsoDate } from "@/shared/lib/dates";
import { Button } from "@/shared/ui/button";
import { ConfirmDialog, Dialog } from "@/shared/ui/dialog";
import { Field, Input, Select, Textarea } from "@/shared/ui/input";
import { useToast } from "@/shared/ui/toast";

const sprintSchema = z.object({
  name: z.string().min(1).max(120),
  goal: z.string().max(280),
  start_date: z.string(),
  end_date: z.string(),
});

type SprintValues = z.infer<typeof sprintSchema>;

export function CreateSprintDialog({
  open,
  onClose,
  workspaceId,
  projectId,
}: {
  open: boolean;
  onClose: () => void;
  workspaceId: string;
  projectId: string;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const createSprint = useCreateSprint(workspaceId, projectId);
  const today = toIsoDate(new Date());
  const form = useForm<SprintValues>({
    resolver: zodResolver(sprintSchema),
    values: {
      name: "",
      goal: "",
      start_date: today,
      end_date: toIsoDate(addDays(new Date(), 13)),
    },
  });

  const onSubmit = form.handleSubmit(async (values) => {
    if (!isValidSprintRange(values.start_date, values.end_date)) {
      form.setError("end_date", { message: t("errors.INVALID_SPRINT_DURATION") });
      return;
    }
    try {
      await createSprint.mutateAsync({
        name: values.name,
        goal: values.goal === "" ? undefined : values.goal,
        start_date: values.start_date,
        end_date: values.end_date,
      });
      form.reset();
      onClose();
    } catch (error) {
      toast.pushError(error);
    }
  });

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={t("sprint.createTitle")}
      footer={
        <>
          <button type="button" className="plain" onClick={onClose}>
            {t("common.cancel")}
          </button>
          <Button type="submit" form="sprint-form" disabled={createSprint.isPending}>
            {t("common.create")}
          </Button>
        </>
      }
    >
      <form
        id="sprint-form"
        onSubmit={(event) => void onSubmit(event)}
        className="grid gap-4"
        noValidate
      >
        <Field
          label={t("sprint.name")}
          htmlFor="sprint-name"
          error={form.formState.errors.name ? t("errors.REQUEST_VALIDATION_ERROR") : undefined}
        >
          <Input id="sprint-name" {...form.register("name")} />
        </Field>
        <Field label={t("sprint.goal")} htmlFor="sprint-goal" hint={t("sprint.goalHint")}>
          <Textarea id="sprint-goal" rows={3} {...form.register("goal")} />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t("sprint.startDate")} htmlFor="sprint-start">
            <Input id="sprint-start" type="date" {...form.register("start_date")} />
          </Field>
          <Field
            label={t("sprint.endDate")}
            htmlFor="sprint-end"
            hint={t("sprint.durationHint")}
            error={form.formState.errors.end_date?.message}
          >
            <Input id="sprint-end" type="date" {...form.register("end_date")} />
          </Field>
        </div>
      </form>
    </Dialog>
  );
}

export function SprintActions({
  workspaceId,
  projectId,
  sprint,
  nextSprint,
}: {
  workspaceId: string;
  projectId: string;
  sprint: Sprint;
  nextSprint?: Sprint;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const startSprint = useStartSprint(workspaceId, projectId);
  const completeSprint = useCompleteSprint(workspaceId, projectId);
  const [confirmComplete, setConfirmComplete] = useState(false);
  const [target, setTarget] = useState<string>("backlog");

  if (sprint.state === "PLANNED") {
    return (
      <Button
        disabled={startSprint.isPending}
        onClick={() => {
          startSprint.mutate(
            { sprintId: sprint.id },
            {
              onError: (error) => {
                toast.pushError(error);
              },
            },
          );
        }}
      >
        {t("sprint.start")}
      </Button>
    );
  }

  if (sprint.state === "ACTIVE") {
    return (
      <>
        <Button
          variant="outline"
          onClick={() => {
            setConfirmComplete(true);
          }}
        >
          {t("sprint.complete")}
        </Button>
        <ConfirmDialog
          open={confirmComplete}
          onClose={() => {
            setConfirmComplete(false);
          }}
          onConfirm={() => {
            completeSprint.mutate(
              {
                sprintId: sprint.id,
                targetSprintId: target === "backlog" ? null : target,
              },
              {
                onSuccess: () => {
                  setConfirmComplete(false);
                },
                onError: (error) => {
                  toast.pushError(error);
                },
              },
            );
          }}
          title={t("sprint.confirmComplete")}
          description={t("sprint.confirmCompleteHint")}
          confirmLabel={t("sprint.complete")}
          pending={completeSprint.isPending}
        >
          <Field label={t("sprint.moveTo")} htmlFor="carryover-target">
            <Select
              id="carryover-target"
              value={target}
              onChange={(event) => {
                setTarget(event.target.value);
              }}
            >
              <option value="backlog">{t("sprint.backlog")}</option>
              {nextSprint ? <option value={nextSprint.id}>{nextSprint.name}</option> : null}
            </Select>
          </Field>
        </ConfirmDialog>
      </>
    );
  }

  return null;
}
