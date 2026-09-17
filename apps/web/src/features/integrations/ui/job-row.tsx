import { useRunImportChunk } from "@/entities/integration/api";
import { jobStateLabelKey } from "@/entities/integration/model";
import type { ImportJob } from "@/shared/api/types";
import { useI18n } from "@/shared/i18n";
import { Button } from "@/shared/ui/button";
import { Badge } from "@/shared/ui/misc";
import { useToast } from "@/shared/ui/toast";

export function JobRow({
  job,
  workspaceId,
  connectionId,
}: {
  job: ImportJob;
  workspaceId: string;
  connectionId: string;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const runChunk = useRunImportChunk(workspaceId, connectionId);
  const stateLabel = t(jobStateLabelKey(job.state));
  return (
    <div className="led-row">
      <div className="grid gap-1">
        <span className="mono text-ash">
          {job.project_key} · {stateLabel}
        </span>
        <span className="num text-sm">
          {t("integrations.imported", { n: job.imported_count })} · cursor {job.start_at}
        </span>
        {job.last_error ? <span className="error-text">{job.last_error}</span> : null}
      </div>
      {job.state !== "DONE" && job.state !== "FAILED" ? (
        <Button
          variant="outline"
          disabled={runChunk.isPending}
          onClick={() => {
            runChunk.mutate(job.id, {
              onError: (error) => {
                toast.pushError(error);
              },
            });
          }}
        >
          {t("integrations.runChunk")}
        </Button>
      ) : (
        <Badge tone={job.state === "DONE" ? "live" : "danger"}>{stateLabel}</Badge>
      )}
    </div>
  );
}
