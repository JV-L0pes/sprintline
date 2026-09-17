import { ArrowLeft, ArrowRight, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import {
  useCreateColumn,
  useDeleteColumn,
  useReorderColumns,
  useUpdateColumn,
} from "@/entities/board/api";
import type { Board, StatusCategory } from "@/shared/api/types";
import { useI18n } from "@/shared/i18n";
import { Button } from "@/shared/ui/button";
import { Dialog } from "@/shared/ui/dialog";
import { Input, Select } from "@/shared/ui/input";
import { useToast } from "@/shared/ui/toast";

const CATEGORIES: StatusCategory[] = ["TODO", "IN_PROGRESS", "DONE"];
const CATEGORY_LABEL: Record<StatusCategory, string> = {
  TODO: "To Do",
  IN_PROGRESS: "In Progress",
  DONE: "Done",
};

export function ColumnsDialog({
  open,
  onClose,
  workspaceId,
  projectId,
  board,
}: {
  open: boolean;
  onClose: () => void;
  workspaceId: string;
  projectId: string;
  board: Board;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const createColumn = useCreateColumn(workspaceId, projectId);
  const updateColumn = useUpdateColumn(workspaceId, projectId);
  const deleteColumn = useDeleteColumn(workspaceId, projectId);
  const reorder = useReorderColumns(workspaceId, projectId);
  const [newName, setNewName] = useState("");
  const [newCategory, setNewCategory] = useState<StatusCategory>("TODO");

  const columns = [...board.columns].sort((a, b) => a.position - b.position);

  const move = (index: number, direction: -1 | 1) => {
    const target = index + direction;
    if (target < 0 || target >= columns.length) {
      return;
    }
    const ids = columns.map((column) => column.id);
    const [moved] = ids.splice(index, 1);
    if (moved === undefined) {
      return;
    }
    ids.splice(target, 0, moved);
    reorder.mutate(ids, {
      onError: (error) => {
        toast.pushError(error);
      },
    });
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={t("board.columnsTitle")}
      footer={
        <button type="button" className="plain" onClick={onClose}>
          {t("common.close")}
        </button>
      }
    >
      <p className="text-sm text-ash">{t("board.columnsHint")}</p>
      <div className="grid gap-3">
        {columns.map((column, index) => (
          <div key={column.id} className="grid gap-2 border-b border-rule pb-3">
            <div className="flex items-center gap-2">
              <Input
                aria-label={t("board.columnName")}
                defaultValue={column.name}
                onBlur={(event) => {
                  const name = event.target.value.trim();
                  if (name && name !== column.name) {
                    updateColumn.mutate(
                      { columnId: column.id, patch: { name } },
                      {
                        onError: (error) => {
                          toast.pushError(error);
                        },
                      },
                    );
                  }
                }}
              />
              <span className="mono w-28 shrink-0 text-ash">{CATEGORY_LABEL[column.category]}</span>
              <button
                type="button"
                className="sq"
                aria-label={t("board.moveLeft")}
                disabled={index === 0}
                onClick={() => {
                  move(index, -1);
                }}
              >
                <ArrowLeft size={14} strokeWidth={2} aria-hidden />
              </button>
              <button
                type="button"
                className="sq"
                aria-label={t("board.moveRight")}
                disabled={index === columns.length - 1}
                onClick={() => {
                  move(index, 1);
                }}
              >
                <ArrowRight size={14} strokeWidth={2} aria-hidden />
              </button>
              <button
                type="button"
                className="sq"
                aria-label={t("board.removeColumn")}
                onClick={() => {
                  deleteColumn.mutate(column.id, {
                    onError: (error) => {
                      toast.pushError(error);
                    },
                  });
                }}
              >
                <Trash2 size={14} strokeWidth={2} aria-hidden />
              </button>
            </div>
            <div className="flex items-center gap-2">
              <label className="lab w-28" htmlFor={`wip-${column.id}`}>
                {t("board.columnWip")}
              </label>
              <Input
                id={`wip-${column.id}`}
                type="number"
                min={1}
                className="w-28"
                placeholder={t("board.columnWipPlaceholder")}
                defaultValue={column.wip_limit ?? ""}
                onBlur={(event) => {
                  const raw = event.target.value.trim();
                  const next = raw === "" ? null : Number(raw);
                  if (next !== null && (!Number.isInteger(next) || next < 1)) {
                    event.target.value = column.wip_limit === null ? "" : String(column.wip_limit);
                    toast.push(t("errors.INVALID_WIP_LIMIT"), "error");
                    return;
                  }
                  if (next === column.wip_limit) {
                    return;
                  }
                  updateColumn.mutate(
                    {
                      columnId: column.id,
                      patch: next === null ? { clear_wip: true } : { wip_limit: next },
                    },
                    {
                      onError: (error) => {
                        toast.pushError(error);
                      },
                    },
                  );
                }}
              />
              <span className="mono text-ash">
                {t("board.itemCount", { n: column.item_count })}
              </span>
            </div>
          </div>
        ))}
      </div>
      <div className="grid gap-2">
        <p className="kicker">{t("board.addColumn")}</p>
        <div className="flex items-end gap-2">
          <Input
            aria-label={t("board.columnName")}
            placeholder={t("board.columnName")}
            value={newName}
            onChange={(event) => {
              setNewName(event.target.value);
            }}
          />
          <Select
            aria-label={t("board.columnCategory")}
            value={newCategory}
            onChange={(event) => {
              setNewCategory(event.target.value as StatusCategory);
            }}
          >
            {CATEGORIES.map((category) => (
              <option key={category} value={category}>
                {CATEGORY_LABEL[category]}
              </option>
            ))}
          </Select>
          <Button
            disabled={createColumn.isPending || newName.trim() === ""}
            onClick={() => {
              createColumn.mutate(
                { name: newName.trim(), category: newCategory },
                {
                  onSuccess: () => {
                    setNewName("");
                  },
                  onError: (error) => {
                    toast.pushError(error);
                  },
                },
              );
            }}
          >
            <Plus size={14} aria-hidden /> {t("common.create")}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
