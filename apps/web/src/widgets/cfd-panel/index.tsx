import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { toCfdChart } from "@/entities/metric/model";
import type { Cfd } from "@/shared/api/types";
import { useI18n } from "@/shared/i18n";
import { AXIS_LINE, AXIS_TICK, renderChartTooltip } from "@/shared/ui/chart";

const STATUS_LABEL: Record<"TODO" | "IN_PROGRESS" | "DONE", string> = {
  TODO: "To Do",
  IN_PROGRESS: "In Progress",
  DONE: "Done",
};

export function CfdPanel({ cfd }: { cfd: Cfd }) {
  const { t, language } = useI18n();
  const rows = toCfdChart(cfd, language);
  const label = (category: "TODO" | "IN_PROGRESS" | "DONE") => STATUS_LABEL[category];
  return (
    <section className="mb-10">
      <div className="sec-head">
        <div>
          <p className="kicker">{t("metrics.title")}</p>
          <h2 className="text-2xl">{t("metrics.cfd")}</h2>
        </div>
        <span className="mono text-ash">{t("metrics.unitItems")}</span>
      </div>
      <div style={{ width: "100%", height: "clamp(220px, 30vh, 320px)" }}>
        <ResponsiveContainer>
          <AreaChart data={rows} margin={{ top: 8, right: 16, bottom: 4, left: -12 }}>
            <CartesianGrid stroke="var(--rule)" vertical={false} />
            <XAxis dataKey="label" tick={AXIS_TICK} axisLine={AXIS_LINE} tickLine={false} />
            <YAxis
              tick={AXIS_TICK}
              axisLine={false}
              tickLine={false}
              width={36}
              allowDecimals={false}
            />
            <Tooltip content={renderChartTooltip} cursor={{ stroke: "var(--rule)" }} />
            <Area
              type="monotone"
              dataKey="TODO"
              name={label("TODO")}
              stackId="1"
              stroke="var(--ash)"
              fill="var(--rule)"
              fillOpacity={0.7}
            />
            <Area
              type="monotone"
              dataKey="IN_PROGRESS"
              name={label("IN_PROGRESS")}
              stackId="1"
              stroke="var(--ash)"
              fill="var(--ash)"
              fillOpacity={0.45}
            />
            <Area
              type="monotone"
              dataKey="DONE"
              name={label("DONE")}
              stackId="1"
              stroke="var(--gold)"
              fill="var(--gold)"
              fillOpacity={0.55}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
