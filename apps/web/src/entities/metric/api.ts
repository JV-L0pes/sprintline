import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/shared/api/client";
import { queryKeys } from "@/shared/api/query";
import type { Burndown, Cfd, FlowTimes, Velocity } from "@/shared/api/types";

export function useBurndown(workspaceId: string | undefined, sprintId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.burndown(workspaceId ?? "", sprintId ?? ""),
    queryFn: () =>
      apiRequest<Burndown>(`/api/v1/workspaces/${workspaceId}/sprints/${sprintId}/burndown`),
    enabled: Boolean(workspaceId && sprintId),
  });
}

export function useCfd(workspaceId: string | undefined, sprintId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.cfd(workspaceId ?? "", sprintId ?? ""),
    queryFn: () => apiRequest<Cfd>(`/api/v1/workspaces/${workspaceId}/sprints/${sprintId}/cfd`),
    enabled: Boolean(workspaceId && sprintId),
  });
}

export function useVelocity(
  workspaceId: string | undefined,
  projectId: string | undefined,
  last = 3,
) {
  return useQuery({
    queryKey: queryKeys.velocity(workspaceId ?? "", projectId ?? "", last),
    queryFn: () =>
      apiRequest<Velocity>(
        `/api/v1/workspaces/${workspaceId}/projects/${projectId}/velocity?last=${String(last)}`,
      ),
    enabled: Boolean(workspaceId && projectId),
  });
}

export function useFlowTimes(workspaceId: string | undefined, projectId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.flowTimes(workspaceId ?? "", projectId ?? ""),
    queryFn: () =>
      apiRequest<FlowTimes>(`/api/v1/workspaces/${workspaceId}/projects/${projectId}/flow-times`),
    enabled: Boolean(workspaceId && projectId),
  });
}
