import { describe, expect, it } from "vitest";
import {
  addDays,
  daysRemaining,
  diffInDays,
  formatDate,
  formatDateFull,
  isValidSprintRange,
  parseIsoDate,
  sprintDayCount,
  toIsoDate,
} from "./dates";

describe("parseIsoDate", () => {
  it("converte datas ISO em UTC sem drift de fuso", () => {
    const date = parseIsoDate("2026-09-07");
    expect(date.getUTCFullYear()).toBe(2026);
    expect(date.getUTCMonth()).toBe(8);
    expect(date.getUTCDate()).toBe(7);
  });

  it("rejeita formato inválido", () => {
    expect(() => parseIsoDate("07/09/2026")).toThrow();
  });
});

describe("sprint ranges", () => {
  it("calcula duração inclusiva", () => {
    expect(sprintDayCount("2026-09-07", "2026-09-20")).toBe(14);
    expect(diffInDays(parseIsoDate("2026-09-07"), parseIsoDate("2026-09-20"))).toBe(13);
  });

  it("valida o range de 7 a 28 dias (Scrum Guide)", () => {
    expect(isValidSprintRange("2026-09-07", "2026-09-13")).toBe(true);
    expect(isValidSprintRange("2026-09-07", "2026-09-12")).toBe(false);
    expect(isValidSprintRange("2026-09-01", "2026-10-01")).toBe(false);
    expect(isValidSprintRange("ontem", "amanha")).toBe(false);
  });

  it("calcula dias restantes sem negativo", () => {
    expect(daysRemaining("2026-09-20", "2026-09-16")).toBe(4);
    expect(daysRemaining("2026-09-10", "2026-09-16")).toBe(0);
  });
});

describe("formatação", () => {
  it("formata datas de forma estavel por locale", () => {
    expect(formatDateFull("2026-09-07", "pt-BR")).toContain("2026");
    expect(formatDate("2026-09-07", "en")).toMatch(/Sep/i);
  });

  it("toIsoDate e addDays são consistentes", () => {
    expect(toIsoDate(parseIsoDate("2026-09-07"))).toBe("2026-09-07");
    expect(toIsoDate(addDays(parseIsoDate("2026-09-07"), 13))).toBe("2026-09-20");
  });
});
