import type { Burndown, Cfd, FlowTimes, Velocity } from "@/shared/api/types";
import { formatDate, formatNumber } from "@/shared/lib/dates";

export interface BurndownChartRow {
  label: string;
  ideal: number;
  remaining: number;
  completed: number;
  scope: number;
}

export function toBurndownChart(burndown: Burndown, language: string): BurndownChartRow[] {
  return burndown.days.map((day) => ({
    label: formatDate(day.date, language),
    ideal: day.ideal,
    remaining: day.remaining,
    completed: day.completed,
    scope: day.scope,
  }));
}

export interface ScopeChangeMarker {
  label: string;
  value: number;
  delta: number;
  kind: "added" | "removed";
}

/** Posiciona os marcadores de mudanca de escopo sobre a linha de restante. */
export function scopeChangeMarkers(burndown: Burndown, language: string): ScopeChangeMarker[] {
  const byDate = new Map(burndown.days.map((day) => [day.date, day]));
  return burndown.scope_changes
    .map((change) => {
      const day = byDate.get(change.date);
      if (!day) {
        return undefined;
      }
      return {
        label: formatDate(change.date, language),
        value: day.remaining,
        delta: change.delta,
        kind: change.kind,
      };
    })
    .filter((marker): marker is ScopeChangeMarker => marker !== undefined);
}

export interface CfdChartRow {
  label: string;
  TODO: number;
  IN_PROGRESS: number;
  DONE: number;
}

export function toCfdChart(cfd: Cfd, language: string): CfdChartRow[] {
  return cfd.days.map((day) => ({
    label: formatDate(day.date, language),
    TODO: day.counts.TODO,
    IN_PROGRESS: day.counts.IN_PROGRESS,
    DONE: day.counts.DONE,
  }));
}

export function velocityAverageLabel(velocity: Velocity, language: string): string {
  const value = formatNumber(velocity.average, language, 1);
  return velocity.unit === "points" ? `${value} pts` : `${value} itens`;
}

export interface FlowRow {
  key: string;
  cycle: number | null;
  lead: number | null;
}

export function flowRows(flow: FlowTimes): FlowRow[] {
  return [
    { key: "p50", cycle: flow.cycle_p50, lead: flow.lead_p50 },
    { key: "p85", cycle: flow.cycle_p85, lead: flow.lead_p85 },
    { key: "p95", cycle: flow.cycle_p95, lead: flow.lead_p95 },
  ];
}

export function flowSummary(flow: FlowTimes): string {
  return String(flow.count);
}
