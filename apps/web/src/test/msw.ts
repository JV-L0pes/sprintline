import { HttpResponse, http } from "msw";
import { setupServer } from "msw/node";

export const handlers = [
  http.post("*/api/v1/auth/refresh", () =>
    HttpResponse.json({ code: "SESSION_NOT_FOUND", detail: "Sessao ausente" }, { status: 401 }),
  ),
  http.get("*/api/v1/meta", () =>
    HttpResponse.json({ app_name: "Sprintline", registration_mode: "open" }),
  ),
];

export const server = setupServer(...handlers);

interface ProblemBody {
  type: string;
  title: string;
  status: number;
  detail: string;
  code: string;
}

export function problemResponse(
  status: number,
  code: string,
  detail: string,
): HttpResponse<ProblemBody> {
  return HttpResponse.json({ type: "about:blank", title: code, status, detail, code }, { status });
}
