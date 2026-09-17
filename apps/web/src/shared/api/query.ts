import { QueryClient } from "@tanstack/react-query";

export const queryKeys = {
  me: ["me"] as const,
  workspaces: ["workspaces"] as const,
  workspace: (workspaceId: string) => ["workspace", workspaceId] as const,
  members: (workspaceId: string) => ["members", workspaceId] as const,
  projects: (workspaceId: string) => ["projects", workspaceId] as const,
  board: (workspaceId: string, projectId: string) => ["board", workspaceId, projectId] as const,
  items: (workspaceId: string, projectId: string) => ["items", workspaceId, projectId] as const,
  sprints: (workspaceId: string, projectId: string) => ["sprints", workspaceId, projectId] as const,
  burndown: (workspaceId: string, sprintId: string) => ["burndown", workspaceId, sprintId] as const,
  cfd: (workspaceId: string, sprintId: string) => ["cfd", workspaceId, sprintId] as const,
  velocity: (workspaceId: string, projectId: string, last: number) =>
    ["velocity", workspaceId, projectId, last] as const,
  flowTimes: (workspaceId: string, projectId: string) =>
    ["flow-times", workspaceId, projectId] as const,
  integrations: (workspaceId: string) => ["integrations", workspaceId] as const,
  jobs: (workspaceId: string, connectionId: string) => ["jobs", workspaceId, connectionId] as const,
};

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 15_000,
        retry: 1,
        refetchOnWindowFocus: true,
      },
      mutations: {
        retry: 0,
      },
    },
  });
}
