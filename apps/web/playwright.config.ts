import { defineConfig, devices } from "@playwright/test";

const e2eEnabled = process.env.CADENCIA_E2E === "1";
// Em CI o uv está no PATH; localmente defina UV_BIN com o caminho completo.
const uvBin = process.env.UV_BIN ?? "uv";

/**
 * E2E roda contra um stack real. Com CADENCIA_E2E=1 o próprio Playwright
 * sobe api (com seed) e web; sem a flag, os testes são pulados.
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  globalTimeout: e2eEnabled ? 240_000 : undefined,
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://127.0.0.1:5173",
    trace: "on-first-retry",
    locale: "pt-BR",
    timezoneId: "America/Sao_Paulo",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: e2eEnabled
    ? [
        {
          command: `${uvBin} run python scripts/seed_demo.py && ${uvBin} run uvicorn cadencia.main:app --port 8000`,
          cwd: "../api",
          url: "http://127.0.0.1:8000/healthz",
          reuseExistingServer: true,
          timeout: 120_000,
          env: {
            CADENCIA_ENVIRONMENT: "development",
            CADENCIA_DATABASE_URL: "sqlite+aiosqlite:///./cadencia-e2e.db",
            CADENCIA_REGISTRATION_MODE: "open",
            CADENCIA_REGISTER_MAX_ATTEMPTS: "10000",
            CADENCIA_LOGIN_MAX_ATTEMPTS: "10000",
          },
        },
        {
          command: "pnpm exec vite --host 127.0.0.1 --port 5173",
          cwd: ".",
          url: "http://127.0.0.1:5173",
          reuseExistingServer: true,
          timeout: 60_000,
        },
      ]
    : undefined,
});
