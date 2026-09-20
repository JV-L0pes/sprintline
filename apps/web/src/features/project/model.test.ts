import { describe, expect, it } from "vitest";
import { suggestProjectKey } from "./model";

describe("suggestProjectKey", () => {
  it("usa a primeira palavra quando tem 3+ letras", () => {
    expect(suggestProjectKey("App Mobile")).toBe("APP");
    expect(suggestProjectKey("Desenvolvimento")).toBe("DESE");
  });

  it("remove acentos", () => {
    expect(suggestProjectKey("Aplicação Financeira")).toBe("APLI");
  });

  it("usa iniciais quando a primeira palavra é curta", () => {
    expect(suggestProjectKey("A B C")).toBe("ABC");
    expect(suggestProjectKey("UX Research")).toBe("UX");
  });

  it("evita colisões sufixando", () => {
    const taken = new Set(["APP", "APP2"]);
    expect(suggestProjectKey("App Mobile", taken)).toBe("APP3");
    expect(suggestProjectKey("App Mobile", new Set(["APP"]))).toBe("APP2");
  });

  it("não começa com dígito e respeita 10 caracteres", () => {
    expect(suggestProjectKey("4x4 App")).toBe("X4");
    expect(suggestProjectKey("ABCDEFGHIJKLMNO")).toBe("ABCD");
  });

  it("cai no padrão PRJ quando o nome não gera chave", () => {
    expect(suggestProjectKey("")).toBe("PRJ");
    expect(suggestProjectKey("42")).toBe("PRJ");
    expect(suggestProjectKey("A")).toBe("PRJ");
    expect(suggestProjectKey("", new Set(["PRJ"]))).toBe("PRJ2");
  });
});
