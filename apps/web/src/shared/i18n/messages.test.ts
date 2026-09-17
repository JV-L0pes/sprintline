import { describe, expect, it } from "vitest";
import { en, pt } from "./messages";

function flatten(object: Record<string, unknown>, prefix = ""): string[] {
  return Object.entries(object).flatMap(([key, value]) => {
    const path = prefix === "" ? key : `${prefix}.${key}`;
    if (typeof value === "string") {
      return [path];
    }
    return flatten(value as Record<string, unknown>, path);
  });
}

describe("dicionarios i18n", () => {
  const ptKeys = flatten(pt).sort();
  const enKeys = flatten(en).sort();

  it("en cobre exatamente as mesmas chaves de pt-BR", () => {
    expect(enKeys).toEqual(ptKeys);
  });

  it("não tem chaves vazias", () => {
    const emptyPt = ptKeys.filter((key) => resolve(pt, key) === "");
    const emptyEn = enKeys.filter((key) => resolve(en, key) === "");
    expect(emptyPt).toEqual([]);
    expect(emptyEn).toEqual([]);
  });

  function resolve(dictionary: Record<string, unknown>, key: string): string | undefined {
    const segments = key.split(".");
    let current: unknown = dictionary;
    for (const segment of segments) {
      if (typeof current !== "object" || current === null) {
        return undefined;
      }
      current = (current as Record<string, unknown>)[segment];
    }
    return typeof current === "string" ? current : undefined;
  }
});
