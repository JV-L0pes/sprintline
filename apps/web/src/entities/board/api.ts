import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/shared/api/client";
import { queryKeys } from "@/shared/api/query";
import type { Board, WorkItem } from "@/shared/api/types";

export function useBoard(workspaceId: string | undefined, projectId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.board(workspaceId ?? "", projectId ?? ""),
    queryFn: () =>
      apiRequest<Board>(`/api/v1/workspaces/${workspaceId}/projects/${projectId}/board`),
    enabled: Boolean(workspaceId && projectId),
  });
}

/** Reagrupa os itens por coluna a partir do estado do board. */
export function groupItemsByColumn(board: Board): Map<string, WorkItem[]> {
  const grouped = new Map<string, WorkItem[]>();
  for (const column of [...board.columns].sort((a, b) => a.position - b.position)) {
    grouped.set(column.id, []);
  }
  for (const item of [...board.items].sort((a, b) => a.position - b.position)) {
    const bucket = grouped.get(item.status_column_id);
    if (bucket) {
      bucket.push(item);
    }
  }
  return grouped;
}

/**
 * Move um item entre colunas/posicoes preservando a ordenacao — usado tanto
 * pelo drag-and-drop quanto pelas atualizacoes otimistas.
 */
export function applyMove(
  items: WorkItem[],
  itemId: string,
  targetColumnId: string,
  targetIndex: number,
): WorkItem[] {
  const moving = items.find((item) => item.id === itemId);
  if (!moving) {
    return items;
  }
  const target = items
    .filter((item) => item.status_column_id === targetColumnId && item.id !== itemId)
    .sort((a, b) => a.position - b.position);
  const index = Math.max(0, Math.min(targetIndex, target.length));
  const ordered = [...target.slice(0, index), moving, ...target.slice(index)];
  const positions = new Map(ordered.map((item, position) => [item.id, position + 1]));
  return items.map((item) => {
    if (item.id === itemId) {
      return { ...item, status_column_id: targetColumnId, position: positions.get(item.id) ?? 1 };
    }
    const nextPosition = positions.get(item.id);
    return nextPosition === undefined ? item : { ...item, position: nextPosition };
  });
}
