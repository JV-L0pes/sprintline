import { describe, expect, it } from "vitest";
import type { Burndown, Cfd, FlowTimes } from "@/shared/api/types";
import { flowRows, scopeChangeMarkers, toBurndownChart, toCfdChart } from "./model";

const burndown: Burndown = {
  sprint_id: "s1",
  sprint_name: "Sprint 1",
  unit: "points",
  start_date: "2026-09-07",
  end_date: "2026-09-18",
  days: [
    { date: "2026-09-07", index: 0, ideal: 13, remaining: 13, completed: 0, scope: 13 },
    { date: "2026-09-08", index: 1, ideal: 11.56, remaining: 13, completed: 0, scope: 13 },
    { date: "2026-09-09", index: 2, ideal: 10.11, remaining: 8, completed: 5, scope: 13 },
    { date: "2026-09-10", index: 3, ideal: 8.67, remaining: 11, completed: 5, scope: 16 },
  ],
  scope_changes: [{ date: "2026-09-10", delta: 3, kind: "added" }],
  totals: { initial_scope: 13, final_scope: 16, completed: 5, unestimated_items: 0 },
};

describe("toBurndownChart", () => {
  it("converte as séries para o formato de gráfico", () => {
    const rows = toBurndownChart(burndown, "pt-BR");
    expect(rows).toHaveLength(4);
    expect(rows[0]?.remaining).toBe(13);
    expect(rows[3]?.scope).toBe(16);
    expect(rows[0]?.label).toBeTruthy();
  });
});

describe("scopeChangeMarkers", () => {
  it("ancora a mudanca de escopo no restante do dia", () => {
    const markers = scopeChangeMarkers(burndown, "pt-BR");
    expect(markers).toHaveLength(1);
    expect(markers[0]?.delta).toBe(3);
    expect(markers[0]?.value).toBe(11);
  });

  it("ignora datas fora da série", () => {
    const markers = scopeChangeMarkers(
      { ...burndown, scope_changes: [{ date: "2026-01-01", delta: 5, kind: "added" }] },
      "pt-BR",
    );
    expect(markers).toEqual([]);
  });
});

describe("toCfdChart", () => {
  it("normaliza contagens ausentes para zero", () => {
    const cfd: Cfd = {
      sprint_id: "s1",
      start_date: "2026-09-07",
      end_date: "2026-09-08",
      days: [
        { date: "2026-09-07", counts: { TODO: 2, IN_PROGRESS: 0, DONE: 0 } },
        {
          date: "2026-09-08",
          counts: { TODO: 0, IN_PROGRESS: 0, DONE: 0 },
        },
      ],
    };
    const rows = toCfdChart(cfd, "pt-BR");
    expect(rows[1]?.TODO).toBe(0);
    expect(rows[0]?.TODO).toBe(2);
  });
});

describe("flowRows", () => {
  it("espelha os percentis de cycle e lead time", () => {
    const flow: FlowTimes = {
      count: 3,
      unit: "days",
      cycle_p50: 1,
      cycle_p85: 2,
      cycle_p95: 3,
      lead_p50: 2,
      lead_p85: 4,
      lead_p95: 5,
    };
    const rows = flowRows(flow);
    expect(rows.map((row) => row.key)).toEqual(["p50", "p85", "p95"]);
    expect(rows[2]?.cycle).toBe(3);
    expect(rows[0]?.lead).toBe(2);
  });
});
