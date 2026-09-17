import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/shared/api/client";
import { queryKeys } from "@/shared/api/query";
import type { Project } from "@/shared/api/types";

export function useProjects(workspaceId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.projects(workspaceId ?? ""),
    queryFn: () => apiRequest<Project[]>(`/api/v1/workspaces/${workspaceId}/projects`),
    enabled: Boolean(workspaceId),
  });
}

export function useCreateProject(workspaceId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: { name: string; key: string; mode?: string }) =>
      apiRequest<Project>(`/api/v1/workspaces/${workspaceId}/projects`, {
        method: "POST",
        body: input,
      }),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: queryKeys.projects(workspaceId) });
    },
  });
}
