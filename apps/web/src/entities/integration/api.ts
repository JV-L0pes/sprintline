import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/shared/api/client";
import { queryKeys } from "@/shared/api/query";
import type { FieldDiscovery, ImportJob, Integration, TrelloBoard } from "@/shared/api/types";

export function useIntegrations(workspaceId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.integrations(workspaceId ?? ""),
    queryFn: () => apiRequest<Integration[]>(`/api/v1/workspaces/${workspaceId}/integrations`),
    enabled: Boolean(workspaceId),
  });
}

export function useJiraAuthorize(workspaceId: string) {
  return useMutation({
    mutationFn: () =>
      apiRequest<{ authorize_url: string }>(
        `/api/v1/workspaces/${workspaceId}/integrations/jira/authorize`,
        { method: "POST" },
      ),
  });
}

export function useDiscoverFields(workspaceId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (connectionId: string) =>
      apiRequest<FieldDiscovery>(
        `/api/v1/workspaces/${workspaceId}/integrations/${connectionId}/fields`,
        { method: "POST" },
      ),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: queryKeys.integrations(workspaceId) });
    },
  });
}

export function useStartImport(workspaceId: string, connectionId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (projectKey: string) =>
      apiRequest<ImportJob>(
        `/api/v1/workspaces/${workspaceId}/integrations/${connectionId}/import`,
        { method: "POST", body: { project_key: projectKey } },
      ),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: queryKeys.jobs(workspaceId, connectionId) });
    },
  });
}

export function useJobs(workspaceId: string | undefined, connectionId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.jobs(workspaceId ?? "", connectionId ?? ""),
    queryFn: () =>
      apiRequest<ImportJob[]>(
        `/api/v1/workspaces/${workspaceId}/integrations/${connectionId}/jobs`,
      ),
    enabled: Boolean(workspaceId && connectionId),
    refetchInterval: 5_000,
  });
}

export function useRunImportChunk(workspaceId: string, connectionId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) =>
      apiRequest<ImportJob>(
        `/api/v1/workspaces/${workspaceId}/integrations/${connectionId}/jobs/${jobId}/run?limit=50`,
        { method: "POST" },
      ),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: queryKeys.jobs(workspaceId, connectionId) });
    },
  });
}

export function useDisconnectIntegration(workspaceId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (connectionId: string) =>
      apiRequest<undefined>(`/api/v1/workspaces/${workspaceId}/integrations/${connectionId}`, {
        method: "DELETE",
      }),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: queryKeys.integrations(workspaceId) });
    },
  });
}

// ------------------------------------------------------------------ Trello ---
export function useTrelloAuthorize(workspaceId: string) {
  return useMutation({
    mutationFn: () =>
      apiRequest<{ authorize_url: string }>(
        `/api/v1/workspaces/${workspaceId}/integrations/trello/authorize`,
        { method: "POST" },
      ),
  });
}

export function useConnectTrello(workspaceId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (token: string) =>
      apiRequest<Integration>(`/api/v1/workspaces/${workspaceId}/integrations/trello/connect`, {
        method: "POST",
        body: { token },
      }),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: queryKeys.integrations(workspaceId) });
    },
  });
}

export function useTrelloBoards(workspaceId: string, connectionId: string | undefined) {
  return useQuery({
    queryKey: ["trello-boards", workspaceId, connectionId ?? ""],
    queryFn: () =>
      apiRequest<TrelloBoard[]>(
        `/api/v1/workspaces/${workspaceId}/integrations/${connectionId ?? ""}/trello/boards`,
      ),
    enabled: Boolean(workspaceId && connectionId),
    staleTime: 60_000,
  });
}

export function useStartTrelloImport(workspaceId: string, connectionId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (boardId: string) =>
      apiRequest<ImportJob>(
        `/api/v1/workspaces/${workspaceId}/integrations/${connectionId}/trello/import`,
        { method: "POST", body: { board_id: boardId } },
      ),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: queryKeys.jobs(workspaceId, connectionId) });
    },
  });
}
