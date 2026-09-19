import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import {
  useArchiveItem,
  useAssignItemToSprint,
  useCreateItem,
  useUpdateItem,
} from "@/entities/work-item/api";
import {
  PRIORITIES,
  priorityLabelKey,
  typeLabelKey,
  WORK_ITEM_TYPES,
} from "@/entities/work-item/model";
import type { Sprint, WorkItem } from "@/shared/api/types";
import { useI18n } from "@/shared/i18n";
import { Button } from "@/shared/ui/button";
import { ConfirmDialog, Dialog } from "@/shared/ui/dialog";
import { Field, Input, Textarea } from "@/shared/ui/input";
import { Select } from "@/shared/ui/select";
import { useToast } from "@/shared/ui/toast";

const FIBONACCI = [1, 2, 3, 5, 8, 13] as const;

const schema = z.object({
  type: z.enum(["EPIC", "STORY", "TASK", "BUG", "SUBTASK"]),
  title: z.string().min(1).max(200),
  description: z.string().max(10_000),
  priority: z.enum(["LOWEST", "LOW", "MEDIUM", "HIGH", "HIGHEST"]),
  story_points: z.string(),
  due_date: z.string(),
  sprint_id: z.string(),
});

type ItemValues = z.infer<typeof schema>;

interface ItemDialogProps {
  open: boolean;
  onClose: () => void;
  workspaceId: string;
  projectId: string;
  item?: WorkItem | null;
  sprints?: Sprint[];
}

export function ItemDialog({
  open,
  onClose,
  workspaceId,
  projectId,
  item,
  sprints,
}: ItemDialogProps) {
  const { t } = useI18n();
  const toast = useToast();
  const createItem = useCreateItem(workspaceId, projectId);
  const updateItem = useUpdateItem(workspaceId, projectId);
  const assignSprint = useAssignItemToSprint(workspaceId, projectId);
  const archiveItem = useArchiveItem(workspaceId, projectId);
  const [confirmingArchive, setConfirmingArchive] = useState(false);

  const form = useForm<ItemValues>({
    resolver: zodResolver(schema),
    values: {
      type: item?.type ?? "STORY",
      title: item?.title ?? "",
      description: item?.description ?? "",
      priority: item?.priority ?? "MEDIUM",
      story_points:
        item?.story_points === null || item?.story_points === undefined
          ? ""
          : String(item.story_points),
      due_date: item?.due_date ?? "",
      sprint_id: item?.sprint_id ?? "",
    },
  });

  const onSubmit = form.handleSubmit(async (values) => {
    const points = values.story_points === "" ? null : Number(values.story_points);
    const sprintId = values.sprint_id === "" ? null : values.sprint_id;
    const assignSprints = sprints !== undefined;
    try {
      if (item) {
        await updateItem.mutateAsync({
          itemId: item.id,
          title: values.title,
          description: values.description,
          priority: values.priority,
          story_points: points,
          clear_points: points === null,
          due_date: values.due_date === "" ? null : values.due_date,
          clear_due_date: values.due_date === "",
        });
        if (assignSprints && sprintId !== item.sprint_id) {
          await assignSprint.mutateAsync({ itemId: item.id, sprintId });
        }
      } else {
        const created = await createItem.mutateAsync({
          type: values.type,
          title: values.title,
          description: values.description,
          priority: values.priority,
          story_points: points,
          due_date: values.due_date === "" ? null : values.due_date,
        });
        if (assignSprints && sprintId !== null) {
          await assignSprint.mutateAsync({ itemId: created.id, sprintId });
        }
      }
      onClose();
      form.reset();
    } catch (error) {
      toast.pushError(error);
    }
  });

  return (
    <>
      <Dialog
        open={open}
        onClose={onClose}
        title={item ? t("item.editItem") : t("item.newItem")}
        footer={
          <>
            {item ? (
              <button
                type="button"
                className="plain mr-auto text-danger"
                onClick={() => {
                  setConfirmingArchive(true);
                }}
              >
                {t("common.archive")}
              </button>
            ) : null}
            <button type="button" className="plain" onClick={onClose}>
              {t("common.cancel")}
            </button>
            <Button
              type="submit"
              form="item-form"
              disabled={createItem.isPending || updateItem.isPending}
            >
              {t("common.save")}
            </Button>
          </>
        }
      >
        <form
          id="item-form"
          onSubmit={(event) => void onSubmit(event)}
          className="grid gap-4"
          noValidate
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t("item.type")} htmlFor="item-type">
              <Controller
                control={form.control}
                name="type"
                render={({ field }) => (
                  <Select
                    id="item-type"
                    value={field.value}
                    onChange={(event) => {
                      field.onChange(event.target.value);
                    }}
                    onBlur={field.onBlur}
                    disabled={Boolean(item)}
                  >
                    {WORK_ITEM_TYPES.map((type) => (
                      <option key={type} value={type}>
                        {t(typeLabelKey(type))}
                      </option>
                    ))}
                  </Select>
                )}
              />
            </Field>
            <Field label={t("item.priority")} htmlFor="item-priority">
              <Controller
                control={form.control}
                name="priority"
                render={({ field }) => (
                  <Select
                    id="item-priority"
                    value={field.value}
                    onChange={(event) => {
                      field.onChange(event.target.value);
                    }}
                    onBlur={field.onBlur}
                  >
                    {PRIORITIES.map((priority) => (
                      <option key={priority} value={priority}>
                        {t(priorityLabelKey(priority))}
                      </option>
                    ))}
                  </Select>
                )}
              />
            </Field>
          </div>
          <Field
            label={t("item.title")}
            htmlFor="item-title"
            error={form.formState.errors.title ? t("errors.REQUEST_VALIDATION_ERROR") : undefined}
          >
            <Input id="item-title" {...form.register("title")} />
          </Field>
          <Field label={t("item.description")} htmlFor="item-description">
            <Textarea id="item-description" rows={4} {...form.register("description")} />
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t("item.points")} htmlFor="item-points" hint={t("item.pointsHint")}>
              <Controller
                control={form.control}
                name="story_points"
                render={({ field }) => (
                  <Select
                    id="item-points"
                    value={field.value}
                    onChange={(event) => {
                      field.onChange(event.target.value);
                    }}
                    onBlur={field.onBlur}
                  >
                    <option value="">{t("item.noEstimate")}</option>
                    {FIBONACCI.map((points) => (
                      <option key={points} value={points}>
                        {points}
                      </option>
                    ))}
                  </Select>
                )}
              />
            </Field>
            <Field label={t("item.dueDate")} htmlFor="item-due">
              <Input id="item-due" type="date" {...form.register("due_date")} />
            </Field>
          </div>
          {sprints !== undefined ? (
            <Field label={t("item.sprint")} htmlFor="item-sprint">
              <Controller
                control={form.control}
                name="sprint_id"
                render={({ field }) => (
                  <Select
                    id="item-sprint"
                    value={field.value}
                    onChange={(event) => {
                      field.onChange(event.target.value);
                    }}
                    onBlur={field.onBlur}
                  >
                    <option value="">{t("item.noSprint")}</option>
                    {sprints
                      .filter((sprint) => sprint.state !== "COMPLETED")
                      .map((sprint) => (
                        <option key={sprint.id} value={sprint.id}>
                          {sprint.name} · {t(`sprint.${sprint.state.toLowerCase()}`)}
                        </option>
                      ))}
                  </Select>
                )}
              />
            </Field>
          ) : null}
        </form>
      </Dialog>
      <ConfirmDialog
        open={confirmingArchive && item !== null && item !== undefined}
        onClose={() => {
          setConfirmingArchive(false);
        }}
        onConfirm={() => {
          if (!item) {
            return;
          }
          void archiveItem
            .mutateAsync(item.id)
            .then(() => {
              toast.push(t("item.archived"));
              setConfirmingArchive(false);
              onClose();
            })
            .catch((error: unknown) => {
              toast.pushError(error);
            });
        }}
        title={t("item.archiveTitle")}
        description={t("item.archiveHint")}
        confirmLabel={t("common.archive")}
        pending={archiveItem.isPending}
      />
    </>
  );
}
