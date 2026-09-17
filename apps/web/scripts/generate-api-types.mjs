#!/usr/bin/env node
/**
 * Gera os tipos do client a partir do OpenAPI da API.
 * Requer a API rodando (pnpm api:dev) ou um openapi.json exportado.
 *
 * Uso:
 *   node scripts/generate-api-types.mjs [url]
 */
import { execFileSync } from "node:child_process";

const url = process.argv[2] ?? "http://localhost:8000/openapi.json";
const output = "src/shared/api/schema.d.ts";

console.log(`Gerando tipos de ${url} -> ${output}`);
execFileSync("npx", ["--yes", "openapi-typescript", url, "-o", output], {
  stdio: "inherit",
  shell: process.platform === "win32",
});
console.log("Concluido. O client em shared/api/client.ts permanece tipado manualmente.");
