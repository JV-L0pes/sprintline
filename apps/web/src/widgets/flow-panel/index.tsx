import { flowRows } from "@/entities/metric/model";
import type { FlowTimes } from "@/shared/api/types";
import { useI18n } from "@/shared/i18n";
import { formatNumber } from "@/shared/lib/dates";
import { EmptyState } from "@/shared/ui/misc";

export function FlowPanel({ flow }: { flow: FlowTimes }) {
  const { t, language } = useI18n();
  const rows = flowRows(flow);
  return (
    <section className="mb-10">
      <div className="sec-head">
        <div>
          <p className="kicker">{t("metrics.sample", { n: flow.count })}</p>
          <h2 className="text-2xl">{t("metrics.flowTimes")}</h2>
        </div>
      </div>
      {flow.count === 0 ? (
        <EmptyState title={t("metrics.empty")} hint={t("metrics.emptyHint")} />
      ) : (
        <div className="statgrid">
          {rows.map((row) => (
            <div key={row.key} className="grid gap-2">
              <p className="k">{t(`metrics.${row.key}`)}</p>
              <p className="v">
                {row.cycle === null ? "—" : formatNumber(row.cycle, language, 1)}
                <span className="mono ml-1 text-ash">d</span>
              </p>
              <p className="mono text-ash">
                {t("metrics.leadTime")}:{" "}
                {row.lead === null ? "—" : formatNumber(row.lead, language, 1)}
                <span className="ml-1">d</span>
              </p>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
