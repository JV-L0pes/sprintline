import { expect, type Page, test } from "@playwright/test";

const enabled = process.env.CADENCIA_E2E === "1";

function sectionByHeading(page: Page, name: string) {
  return page.locator("section").filter({ has: page.getByRole("heading", { name, exact: true }) });
}

test.describe("jornada principal", () => {
  test.skip(!enabled, "Requer stack completo; habilite com CADENCIA_E2E=1");

  test("registro → projeto → item → sprint → burndown", async ({ page }) => {
    const suffix = String(Date.now());
    const itemTitle = `Primeira história ${suffix}`;

    await page.goto("/login");
    await page.getByRole("link", { name: /criar conta/i }).click();

    await page.getByLabel(/nome/i).fill("E2E Runner");
    await page.getByLabel(/email/i).fill(`e2e-${suffix}@example.com`);
    await page.getByLabel(/senha/i).fill("senha-super-secreta");
    await page.getByRole("button", { name: /criar conta/i }).click();

    await page.getByRole("button", { name: /novo workspace/i }).click();
    await page.getByLabel(/nome/i).fill(`Workspace ${suffix}`);
    await page.getByRole("button", { name: /^criar$/i }).click();

    await page.getByRole("button", { name: /novo projeto/i }).click();
    await page.getByLabel(/nome/i).fill("App E2E");
    await page.getByLabel(/chave/i).fill("E2E");
    await page.getByRole("button", { name: /^criar$/i }).click();

    await expect(page.getByText(/nenhuma sprint ativa/i)).toBeVisible();

    await page
      .getByRole("button", { name: /novo item/i })
      .first()
      .click();
    await page.getByLabel(/título/i).fill(itemTitle);
    await page.getByRole("button", { name: /salvar/i }).click();
    await expect(page.getByText(itemTitle)).toBeVisible();

    await page.getByRole("button", { name: /nova sprint/i }).click();
    await page.getByLabel(/nome/i).fill("Sprint E2E");
    await page.getByLabel(/objetivo/i).fill("Validar o fluxo completo de ponta a ponta");
    await page.getByRole("button", { name: /^criar$/i }).click();

    // Backlog: espera a pagina montar (o board também tem o item com o mesmo título)
    await page.getByRole("link", { name: /backlog/i }).click();
    const backlogSection = sectionByHeading(page, "Product Backlog");
    await expect(backlogSection).toBeVisible();

    // Planeja o item na sprint pelo dialogo (caminho acessível e deterministico;
    // o arrasto fica num handle dedicado fora do alvo de clique)
    await backlogSection.getByRole("button", { name: new RegExp(itemTitle) }).click();
    await page
      .getByLabel("Sprint", { exact: true })
      .selectOption({ label: "Sprint E2E · Planejada" });
    await page.getByRole("button", { name: /salvar/i }).click();

    const sprintSection = sectionByHeading(page, "Sprint E2E");
    await expect(sprintSection.getByText(itemTitle)).toBeVisible();

    // Inicia a sprint e confere o header
    await page.getByRole("link", { name: /board/i }).click();
    await expect(page.getByRole("button", { name: /novo item/i }).first()).toBeVisible();
    await page.getByRole("button", { name: /iniciar sprint/i }).click();
    await expect(page.getByRole("heading", { name: "Sprint E2E" })).toBeVisible();
    await expect(page.getByText(/0\/0 pts/)).toBeVisible();

    // Métricas reais a partir do event log
    await page.getByRole("link", { name: /métricas/i }).click();
    await expect(page.getByRole("heading", { name: /burndown/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: /velocity/i })).toBeVisible();
    await expect(page.getByText(/escopo/i).first()).toBeVisible();
  });
});
