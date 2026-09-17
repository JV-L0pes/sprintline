import { describe, expect, it } from "vitest";
import type { Sprint } from "@/shared/api/types";
import {
  activeSprint,
  defaultSprint,
  plannedSprints,
  progressPercentage,
  sortSprints,
} from "./model";

function sprint(id: string, state: Sprint["state"], startDate: string): Sprint {
  return {
    id,
    board_id: "b1",
    name: `Sprint ${id}`,
    goal: "g",
    state,
    start_date: startDate,
    end_date: startDate,
    completed_at: null,
    total_items: 4,
    done_items: 2,
    total_points: 10,
    done_points: 5,
  };
}

const sprints = [
  sprint("3", "PLANNED", "2026-10-01"),
  sprint("1", "COMPLETED", "2026-09-01"),
  sprint("2", "ACTIVE", "2026-09-15"),
];

describe("sprint model", () => {
  it("ordena por data de inicio", () => {
    expect(sortSprints(sprints).map((item) => item.id)).toEqual(["1", "2", "3"]);
  });

  it("encontra a sprint ativa", () => {
    expect(activeSprint(sprints)?.id).toBe("2");
    expect(activeSprint([sprint("9", "PLANNED", "2026-10-01")])).toBeUndefined();
  });

  it("lista apenas planejadas em ordem", () => {
    expect(plannedSprints(sprints).map((item) => item.id)).toEqual(["3"]);
  });

  it("seleciona a sprint padrão: ativa > concluída > planejada", () => {
    expect(defaultSprint(sprints)?.id).toBe("2");
    expect(defaultSprint([sprint("1", "COMPLETED", "2026-09-01")])?.id).toBe("1");
    expect(defaultSprint([sprint("3", "PLANNED", "2026-10-01")])?.id).toBe("3");
    expect(defaultSprint([])).toBeUndefined();
  });

  it("calcula progresso por pontos com fallback para itens", () => {
    expect(progressPercentage(sprint("1", "ACTIVE", "2026-09-01"))).toBe(50);
    expect(progressPercentage({ ...sprint("1", "ACTIVE", "2026-09-01"), total_points: 0 })).toBe(
      50,
    );
    expect(
      progressPercentage({
        ...sprint("1", "ACTIVE", "2026-09-01"),
        total_points: 0,
        total_items: 0,
      }),
    ).toBe(0);
  });
});
