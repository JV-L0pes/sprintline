import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/shared/api/client";
import { queryKeys } from "@/shared/api/query";
import type { Sprint } from "@/shared/api/types";

export function useSprints(workspaceId: string | undefined, projectId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.sprints(workspaceId ?? "", projectId ?? ""),
    queryFn: () =>
      apiRequest<Sprint[]>(`/api/v1/workspaces/${workspaceId}/projects/${projectId}/sprints`),
    enabled: Boolean(workspaceId && projectId),
  });
}

export function useCreateSprint(workspaceId: string, projectId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: { name: string; goal?: string; start_date: string; end_date: string }) =>
      apiRequest<Sprint>(`/api/v1/workspaces/${workspaceId}/projects/${projectId}/sprints`, {
        method: "POST",
        body: input,
      }),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: queryKeys.sprints(workspaceId, projectId) });
    },
  });
}

function useSprintAction(workspaceId: string, projectId: string, action: "start" | "complete") {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({
      sprintId,
      targetSprintId,
    }: {
      sprintId: string;
      targetSprintId?: string | null;
    }) =>
      apiRequest<Sprint>(`/api/v1/workspaces/${workspaceId}/sprints/${sprintId}/${action}`, {
        method: "POST",
        body: action === "complete" ? { target_sprint_id: targetSprintId ?? null } : undefined,
      }),
    onSuccess: async () => {
      await Promise.all([
        client.invalidateQueries({ queryKey: queryKeys.sprints(workspaceId, projectId) }),
        client.invalidateQueries({ queryKey: queryKeys.items(workspaceId, projectId) }),
        client.invalidateQueries({ queryKey: queryKeys.board(workspaceId, projectId) }),
        client.invalidateQueries({ queryKey: queryKeys.burndown(workspaceId, "") }),
      ]);
    },
  });
}

export function useStartSprint(workspaceId: string, projectId: string) {
  return useSprintAction(workspaceId, projectId, "start");
}

export function useCompleteSprint(workspaceId: string, projectId: string) {
  return useSprintAction(workspaceId, projectId, "complete");
}
