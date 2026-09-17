import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/shared/api/client";
import { queryKeys } from "@/shared/api/query";
import type { Workspace } from "@/shared/api/types";

export function useWorkspaces(enabled = true) {
  return useQuery({
    queryKey: queryKeys.workspaces,
    queryFn: () => apiRequest<Workspace[]>("/api/v1/workspaces"),
    enabled,
  });
}

export function useCreateWorkspace() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: { name: string; timezone?: string }) =>
      apiRequest<Workspace>("/api/v1/workspaces", { method: "POST", body: input }),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: queryKeys.workspaces });
    },
  });
}

export function findWorkspaceBySlug(
  workspaces: Workspace[] | undefined,
  slug: string | undefined,
): Workspace | undefined {
  if (!workspaces || !slug) {
    return undefined;
  }
  return workspaces.find((workspace) => workspace.slug === slug);
}
