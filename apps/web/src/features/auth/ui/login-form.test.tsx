import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http } from "msw";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { SessionProvider } from "@/entities/session";
import { I18nProvider } from "@/shared/i18n";
import { ThemeProvider } from "@/shared/lib/theme";
import { ToastProvider } from "@/shared/ui/toast";
import { problemResponse, server } from "@/test/msw";
import { LoginForm } from "./login-form";

function renderForm() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <I18nProvider>
      <ThemeProvider>
        <QueryClientProvider client={queryClient}>
          <SessionProvider>
            <ToastProvider>
              <MemoryRouter>
                <LoginForm />
              </MemoryRouter>
            </ToastProvider>
          </SessionProvider>
        </QueryClientProvider>
      </ThemeProvider>
    </I18nProvider>,
  );
}

describe("LoginForm", () => {
  beforeEach(() => {
    localStorage.setItem("cadencia-lang", "pt-BR");
  });

  it("mostra erro traduzido quando as credenciais sao invalidas", async () => {
    server.use(
      http.post("*/api/v1/auth/login", () =>
        problemResponse(401, "INVALID_CREDENTIALS", "Credenciais invalidas"),
      ),
    );
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText(/email/i), "dev@example.com");
    await user.type(screen.getByLabelText(/senha/i), "senha-secreta-1");
    await user.click(screen.getByRole("button", { name: /entrar/i }));

    expect(await screen.findByText("Email ou senha incorretos.")).toBeInTheDocument();
  });

  it("valida email antes de chamar a API", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText(/email/i), "nao-e-email");
    await user.type(screen.getByLabelText(/senha/i), "qualquer-coisa");
    await user.click(screen.getByRole("button", { name: /entrar/i }));

    expect(await screen.findByRole("button", { name: /entrar/i })).toBeInTheDocument();
  });
});
