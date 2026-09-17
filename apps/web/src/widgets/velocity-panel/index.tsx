import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { velocityAverageLabel } from "@/entities/metric/model";
import type { Velocity } from "@/shared/api/types";
import { useI18n } from "@/shared/i18n";
import { AXIS_LINE, AXIS_TICK, renderChartTooltip } from "@/shared/ui/chart";

export function VelocityPanel({ velocity, window = 3 }: { velocity: Velocity; window?: number }) {
  const { t, language } = useI18n();
  const rows = velocity.sprints.map((sprint) => ({
    name: sprint.name,
    committed: sprint.committed,
    completed: sprint.completed,
    added: sprint.added,
    removed: sprint.removed,
  }));
  return (
    <section className="mb-10">
      <div className="sec-head">
        <div>
          <p className="kicker">{t("metrics.average", { n: window })}</p>
          <h2 className="text-2xl">{t("metrics.velocity")}</h2>
        </div>
        <span className="num text-2xl font-extrabold tracking-tight">
          {velocityAverageLabel(velocity, language)}
        </span>
      </div>
      <div style={{ width: "100%", height: "clamp(220px, 30vh, 320px)" }}>
        <ResponsiveContainer>
          <BarChart data={rows} margin={{ top: 8, right: 16, bottom: 4, left: -12 }}>
            <CartesianGrid stroke="var(--rule)" vertical={false} />
            <XAxis dataKey="name" tick={AXIS_TICK} axisLine={AXIS_LINE} tickLine={false} />
            <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={40} />
            <Tooltip content={renderChartTooltip} cursor={{ fill: "var(--hover-bg)" }} />
            <Bar dataKey="committed" name={t("metrics.committed")} fill="var(--rule)" />
            <Bar dataKey="completed" name={t("metrics.completed")} fill="var(--gold)" />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="led mt-4">
        {rows.map((row) => (
          <div key={row.name} className="led-row">
            <span className="text-sm font-semibold">{row.name}</span>
            <span className="mono text-ash">
              +{row.added} / −{row.removed} · {row.completed}/{row.committed}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
