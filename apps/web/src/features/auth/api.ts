import { useMutation } from "@tanstack/react-query";
import { apiRequest } from "@/shared/api/client";

export function useChangeOwnPassword() {
  return useMutation({
    mutationFn: ({
      currentPassword,
      newPassword,
    }: {
      currentPassword: string;
      newPassword: string;
    }) =>
      apiRequest<undefined>("/api/v1/auth/password", {
        method: "POST",
        body: { current_password: currentPassword, new_password: newPassword },
      }),
  });
}
