import type { SessionResponse } from "./types";

const API_BASE: string = (import.meta.env.VITE_API_URL as string | undefined) ?? "";

export interface ProblemField {
  loc: string[];
  msg: string;
  type: string;
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    readonly detail: string,
    readonly fields: ProblemField[] = [],
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

let accessToken: string | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
}

async function rawRequest(path: string, options: RequestOptions): Promise<Response> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }
  return fetch(`${API_BASE}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    credentials: "include",
    signal: options.signal,
  });
}

/** Renova a sessão usando o cookie httpOnly; reutilizado no boot do app. */
export async function silentRefresh(): Promise<SessionResponse | null> {
  try {
    const response = await rawRequest("/api/v1/auth/refresh", { method: "POST" });
    if (!response.ok) {
      return null;
    }
    const session = (await response.json()) as SessionResponse;
    setAccessToken(session.access_token);
    return session;
  } catch {
    return null;
  }
}

async function toApiError(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as {
      code?: string;
      detail?: string;
      errors?: ProblemField[];
    };
    return new ApiError(
      response.status,
      body.code ?? `HTTP_${String(response.status)}`,
      body.detail ?? response.statusText,
      body.errors ?? [],
    );
  } catch {
    return new ApiError(response.status, `HTTP_${String(response.status)}`, response.statusText);
  }
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const isAuthEndpoint = path.startsWith("/api/v1/auth/") || path.startsWith("/api/v1/invites/");
  let response = await rawRequest(path, options);
  if (response.status === 401 && !isAuthEndpoint && accessToken !== null) {
    const refreshed = await silentRefresh();
    if (refreshed) {
      response = await rawRequest(path, options);
    }
  }
  if (!response.ok) {
    throw await toApiError(response);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}
