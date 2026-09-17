import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/shared/api/client";
import { queryKeys } from "@/shared/api/query";
import type { Member, Workspace } from "@/shared/api/types";

export function useMembers(workspaceId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.members(workspaceId ?? ""),
    queryFn: () => apiRequest<Member[]>(`/api/v1/workspaces/${workspaceId}/members`),
    enabled: Boolean(workspaceId),
  });
}

export function useInviteMember(workspaceId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: { email: string; role: string }) =>
      apiRequest<{ invite_id: string; token: string; expires_at: string }>(
        `/api/v1/workspaces/${workspaceId}/invites`,
        { method: "POST", body: input },
      ),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: queryKeys.members(workspaceId) });
    },
  });
}

export function useAcceptInvite() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (token: string) =>
      apiRequest<{ workspace: Workspace }>(`/api/v1/invites/${token}/accept`, {
        method: "POST",
      }),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: queryKeys.workspaces });
    },
  });
}
