import { useI18n } from "@/shared/i18n";
import { formatNumber } from "@/shared/lib/dates";

export interface TooltipRow {
  name?: string | number;
  value?: number | string | (number | string)[];
  color?: string;
}

export interface ChartTooltipProps {
  active?: boolean;
  payload?: readonly TooltipRow[];
  label?: string | number;
}

export function ChartTooltip({ active, payload, label }: ChartTooltipProps) {
  const { language } = useI18n();
  if (!active || !payload || payload.length === 0) {
    return null;
  }
  return (
    <div className="chart-tip grid gap-1">
      <span>{label}</span>
      {payload.map((row, index) => {
        if (row.value === undefined || Array.isArray(row.value)) {
          return null;
        }
        return (
          <span key={index} className="flex items-center gap-2">
            <span
              aria-hidden
              style={{ background: row.color ?? "var(--ink)" }}
              className="inline-block h-[2px] w-4"
            />
            <span className="v">
              {String(row.name ?? "")}:{" "}
              {typeof row.value === "number" ? formatNumber(row.value, language, 1) : row.value}
            </span>
          </span>
        );
      })}
    </div>
  );
}

/** Adapter para o prop `content` do Recharts sem vazar tipos internos. */
export function renderChartTooltip(props: unknown): React.ReactElement | null {
  return <ChartTooltip {...(props as ChartTooltipProps)} />;
}

export const AXIS_TICK = {
  fontSize: 10,
  fill: "var(--ash)",
  fontFamily: "var(--font-mono)",
} as const;

export const AXIS_LINE = { stroke: "var(--rule)" } as const;
