import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { applyMove, useBoard } from "@/entities/board/api";
import { apiRequest } from "@/shared/api/client";
import { queryKeys } from "@/shared/api/query";
import type { Board, WorkItem } from "@/shared/api/types";

export function useItems(workspaceId: string | undefined, projectId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.items(workspaceId ?? "", projectId ?? ""),
    queryFn: () =>
      apiRequest<WorkItem[]>(`/api/v1/workspaces/${workspaceId}/projects/${projectId}/items`),
    enabled: Boolean(workspaceId && projectId),
  });
}

export interface CreateItemInput {
  type: string;
  title: string;
  description?: string;
  priority?: string;
  story_points?: number | null;
  due_date?: string | null;
}

export function useCreateItem(workspaceId: string, projectId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateItemInput) =>
      apiRequest<WorkItem>(`/api/v1/workspaces/${workspaceId}/projects/${projectId}/items`, {
        method: "POST",
        body: input,
      }),
    onSuccess: async () => {
      await Promise.all([
        client.invalidateQueries({ queryKey: queryKeys.board(workspaceId, projectId) }),
        client.invalidateQueries({ queryKey: queryKeys.items(workspaceId, projectId) }),
      ]);
    },
  });
}

export function useUpdateItem(workspaceId: string, projectId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ itemId, ...changes }: { itemId: string } & Record<string, unknown>) =>
      apiRequest<WorkItem>(`/api/v1/workspaces/${workspaceId}/items/${itemId}`, {
        method: "PATCH",
        body: changes,
      }),
    onSuccess: async () => {
      await Promise.all([
        client.invalidateQueries({ queryKey: queryKeys.board(workspaceId, projectId) }),
        client.invalidateQueries({ queryKey: queryKeys.items(workspaceId, projectId) }),
      ]);
    },
  });
}

export function useMoveItem(workspaceId: string, projectId: string) {
  const client = useQueryClient();
  const boardKey = queryKeys.board(workspaceId, projectId);
  return useMutation({
    mutationFn: ({
      itemId,
      columnId,
      index,
      expectedVersion,
    }: {
      itemId: string;
      columnId: string;
      index: number;
      expectedVersion?: number;
    }) =>
      apiRequest<{ item: WorkItem; wip_warning: boolean }>(
        `/api/v1/workspaces/${workspaceId}/items/${itemId}/move`,
        {
          method: "POST",
          body: { column_id: columnId, index, expected_version: expectedVersion },
        },
      ),
    onMutate: async ({ itemId, columnId, index }) => {
      await client.cancelQueries({ queryKey: boardKey });
      const previous = client.getQueryData<Board>(boardKey);
      if (previous) {
        client.setQueryData<Board>(boardKey, {
          ...previous,
          items: applyMove(previous.items, itemId, columnId, index),
        });
      }
      return { previous };
    },
    onError: (_error, _variables, context) => {
      if (context?.previous) {
        client.setQueryData(boardKey, context.previous);
      }
    },
    onSettled: async () => {
      await client.invalidateQueries({ queryKey: boardKey });
    },
  });
}

export function useArchiveItem(workspaceId: string, projectId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (itemId: string) =>
      apiRequest(`/api/v1/workspaces/${workspaceId}/items/${itemId}`, {
        method: "DELETE",
      }),
    onSuccess: async () => {
      await Promise.all([
        client.invalidateQueries({ queryKey: queryKeys.board(workspaceId, projectId) }),
        client.invalidateQueries({ queryKey: queryKeys.items(workspaceId, projectId) }),
      ]);
    },
  });
}

export function useAssignItemToSprint(workspaceId: string, projectId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ itemId, sprintId }: { itemId: string; sprintId: string | null }) =>
      apiRequest<WorkItem>(`/api/v1/workspaces/${workspaceId}/items/${itemId}/sprint`, {
        method: "PUT",
        body: { sprint_id: sprintId },
      }),
    onSettled: async () => {
      await Promise.all([
        client.invalidateQueries({ queryKey: queryKeys.items(workspaceId, projectId) }),
        client.invalidateQueries({ queryKey: queryKeys.board(workspaceId, projectId) }),
        client.invalidateQueries({ queryKey: queryKeys.sprints(workspaceId, projectId) }),
      ]);
    },
  });
}

export { useBoard };
