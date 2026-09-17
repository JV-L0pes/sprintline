import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { scopeChangeMarkers, toBurndownChart } from "@/entities/metric/model";
import type { Burndown } from "@/shared/api/types";
import { useI18n } from "@/shared/i18n";
import { formatNumber } from "@/shared/lib/dates";
import { AXIS_LINE, AXIS_TICK, renderChartTooltip } from "@/shared/ui/chart";

export function BurndownPanel({ burndown }: { burndown: Burndown }) {
  const { t, language } = useI18n();
  const rows = toBurndownChart(burndown, language);
  const markers = scopeChangeMarkers(burndown, language);
  const unit = burndown.unit === "points" ? t("metrics.unitPoints") : t("metrics.unitItems");

  return (
    <section className="mb-10">
      <div className="sec-head">
        <div>
          <p className="kicker">{burndown.sprint_name}</p>
          <h2 className="text-2xl">{t("metrics.burndown")}</h2>
        </div>
        <span className="mono text-ash">{unit}</span>
      </div>
      <div style={{ width: "100%", height: "clamp(300px, 42vh, 460px)" }}>
        <ResponsiveContainer>
          <LineChart data={rows} margin={{ top: 12, right: 16, bottom: 4, left: -12 }}>
            <CartesianGrid stroke="var(--rule)" vertical={false} />
            <XAxis dataKey="label" tick={AXIS_TICK} axisLine={AXIS_LINE} tickLine={false} />
            <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={44} />
            <Tooltip content={renderChartTooltip} cursor={{ stroke: "var(--rule)" }} />
            <Line
              type="monotone"
              dataKey="remaining"
              name={t("metrics.remaining")}
              stroke="var(--ink)"
              strokeWidth={2}
              dot={{ r: 2.5, fill: "var(--paper)", stroke: "var(--ink)", strokeWidth: 1.5 }}
              activeDot={{ r: 4 }}
            />
            <Line
              type="monotone"
              dataKey="ideal"
              name={t("metrics.ideal")}
              stroke="var(--ash)"
              strokeWidth={1.5}
              strokeDasharray="5 5"
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="completed"
              name={t("metrics.completed")}
              stroke="var(--gold)"
              strokeWidth={1.5}
              dot={false}
            />
            {markers.map((marker) => (
              <ReferenceDot
                key={`${marker.label}-${String(marker.delta)}`}
                x={marker.label}
                y={marker.value}
                r={4}
                fill="var(--gold-fill)"
                stroke="var(--gold)"
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="statgrid mt-4">
        <div>
          <p className="k">{t("metrics.scope")} (inicial)</p>
          <p className="v">{formatNumber(burndown.totals.initial_scope, language, 0)}</p>
        </div>
        <div>
          <p className="k">{t("metrics.scope")} (final)</p>
          <p className="v">{formatNumber(burndown.totals.final_scope, language, 0)}</p>
        </div>
        <div>
          <p className="k">{t("metrics.completed")}</p>
          <p className="v text-gold">{formatNumber(burndown.totals.completed, language, 0)}</p>
        </div>
        <div>
          <p className="k">{t("metrics.scopeChange")}</p>
          <p className="v">{burndown.scope_changes.length}</p>
        </div>
      </div>
      {burndown.totals.unestimated_items > 0 ? (
        <p className="mono mt-3 text-ash">
          {t("metrics.unestimated", { n: burndown.totals.unestimated_items })}
        </p>
      ) : null}
    </section>
  );
}
