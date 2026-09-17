import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "./client";
import type { Meta } from "./types";

/** Config pública da instância (ex.: modo de registro). */
export function useMeta() {
  return useQuery({
    queryKey: ["meta"],
    queryFn: () => apiRequest<Meta>("/api/v1/meta"),
    staleTime: Number.POSITIVE_INFINITY,
  });
}
