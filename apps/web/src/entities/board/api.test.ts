import { describe, expect, it } from "vitest";
import type { Board, WorkItem } from "@/shared/api/types";
import { applyMove, groupItemsByColumn } from "./api";

function item(id: string, columnId: string, position: number): WorkItem {
  return {
    id,
    project_id: "p1",
    key: `APP-${id}`,
    type: "STORY",
    title: `Item ${id}`,
    description: "",
    parent_id: null,
    status_column_id: columnId,
    status_category: "TODO",
    story_points: 3,
    priority: "MEDIUM",
    assignee_id: null,
    sprint_id: null,
    position,
    due_date: null,
    created_at: "2026-09-01T10:00:00Z",
    updated_at: null,
    done_at: null,
    first_in_progress_at: null,
    version: 1,
  };
}

const board: Board = {
  id: "b1",
  project_id: "p1",
  name: "Board",
  columns: [
    { id: "todo", name: "To Do", position: 0, category: "TODO", wip_limit: null, item_count: 0 },
    {
      id: "doing",
      name: "In Progress",
      position: 1,
      category: "IN_PROGRESS",
      wip_limit: null,
      item_count: 0,
    },
    { id: "done", name: "Done", position: 2, category: "DONE", wip_limit: null, item_count: 0 },
  ],
  items: [item("1", "todo", 1), item("2", "todo", 2), item("3", "todo", 3)],
};

describe("groupItemsByColumn", () => {
  it("agrupa por coluna mantendo a ordem de posicao", () => {
    const grouped = groupItemsByColumn(board);
    expect(grouped.get("todo")?.map((entry) => entry.id)).toEqual(["1", "2", "3"]);
    expect(grouped.get("done")).toEqual([]);
  });
});

describe("applyMove", () => {
  it("move para outra coluna reindexando posicoes", () => {
    const moved = applyMove(board.items, "2", "done", 0);
    const movedItem = moved.find((entry) => entry.id === "2");
    expect(movedItem?.status_column_id).toBe("done");
    expect(movedItem?.position).toBe(1);
    expect(
      moved.filter((entry) => entry.status_column_id === "todo").map((entry) => entry.id),
    ).toEqual(["1", "3"]);
  });

  it("reordena dentro da mesma coluna", () => {
    const moved = applyMove(board.items, "3", "todo", 0);
    const ordered = moved
      .filter((entry) => entry.status_column_id === "todo")
      .sort((a, b) => a.position - b.position)
      .map((entry) => entry.id);
    expect(ordered).toEqual(["3", "1", "2"]);
  });

  it("faz clamp de indice fora do range", () => {
    const moved = applyMove(board.items, "1", "doing", 99);
    const movedItem = moved.find((entry) => entry.id === "1");
    expect(movedItem?.status_column_id).toBe("doing");
    expect(movedItem?.position).toBe(1);
  });

  it("ignora item inexistente", () => {
    const moved = applyMove(board.items, "missing", "done", 0);
    expect(moved).toBe(board.items);
  });
});
