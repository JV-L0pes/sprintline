import { describe, expect, it } from "vitest";
import { jobStateLabelKey, parseTrelloToken } from "./model";

describe("parseTrelloToken", () => {
  it("extrai o token do fragmento retornado pelo Trello", () => {
    expect(parseTrelloToken("#token=abc123")).toBe("abc123");
    expect(parseTrelloToken("token=abc123")).toBe("abc123");
    expect(parseTrelloToken("#token=abc123&expiration=never")).toBe("abc123");
  });

  it("retorna null quando nao ha token", () => {
    expect(parseTrelloToken("")).toBeNull();
    expect(parseTrelloToken("#")).toBeNull();
    expect(parseTrelloToken("#foo=bar")).toBeNull();
    expect(parseTrelloToken("#token=")).toBeNull();
  });
});

describe("jobStateLabelKey", () => {
  it("mapeia os estados de job para chaves de traducao", () => {
    expect(jobStateLabelKey("DONE")).toBe("integrations.done");
    expect(jobStateLabelKey("RUNNING")).toBe("integrations.running");
    expect(jobStateLabelKey("FAILED")).toBe("integrations.failed");
    expect(jobStateLabelKey("PENDING")).toBe("integrations.pending");
    expect(jobStateLabelKey("DESCONHECIDO")).toBe("integrations.pending");
  });
});
