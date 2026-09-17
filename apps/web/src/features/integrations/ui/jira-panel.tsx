import { useState } from "react";
import {
  useDisconnectIntegration,
  useDiscoverFields,
  useIntegrations,
  useJiraAuthorize,
  useJobs,
  useStartImport,
} from "@/entities/integration/api";
import type { Integration } from "@/shared/api/types";
import { useI18n } from "@/shared/i18n";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { EmptyState } from "@/shared/ui/misc";
import { useToast } from "@/shared/ui/toast";
import { JobRow } from "./job-row";

function ConnectedJira({
  integration,
  workspaceId,
}: {
  integration: Integration;
  workspaceId: string;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const discover = useDiscoverFields(workspaceId);
  const startImport = useStartImport(workspaceId, integration.id);
  const disconnect = useDisconnectIntegration(workspaceId);
  const jobs = useJobs(workspaceId, integration.id);
  const [projectKey, setProjectKey] = useState("");

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="grid gap-1">
          <span className="live">
            <i aria-hidden /> {t("integrations.connected", { site: integration.site_url })}
          </span>
          <span className="mono text-ash">
            {integration.story_points_field
              ? t("integrations.storyPointsField", { field: integration.story_points_field })
              : t("integrations.discover")}
          </span>
        </div>
        <div className="flex gap-3">
          <Button
            variant="outline"
            disabled={discover.isPending}
            onClick={() => {
              discover.mutate(integration.id, {
                onError: (error) => {
                  toast.pushError(error);
                },
              });
            }}
          >
            {t("integrations.discover")}
          </Button>
          <Button
            variant="danger"
            disabled={disconnect.isPending}
            onClick={() => {
              disconnect.mutate(integration.id, {
                onError: (error) => {
                  toast.pushError(error);
                },
              });
            }}
          >
            {t("integrations.disconnect")}
          </Button>
        </div>
      </div>
      <div className="flex items-end gap-3">
        <label className="field flex-1" htmlFor={`import-${integration.id}`}>
          <span className="lab">{t("integrations.projectKey")}</span>
          <Input
            id={`import-${integration.id}`}
            value={projectKey}
            onChange={(event) => {
              setProjectKey(event.target.value.toUpperCase());
            }}
            placeholder="SCRUM"
          />
        </label>
        <Button
          disabled={startImport.isPending || projectKey.length === 0}
          onClick={() => {
            startImport.mutate(projectKey, {
              onError: (error) => {
                toast.pushError(error);
              },
            });
          }}
        >
          {t("integrations.startImport")}
        </Button>
      </div>
      <div>
        <p className="kicker">{t("integrations.jobs")}</p>
        <div className="led">
          {(jobs.data ?? []).map((job) => (
            <JobRow
              key={job.id}
              job={job}
              workspaceId={workspaceId}
              connectionId={integration.id}
            />
          ))}
          {jobs.data && jobs.data.length === 0 ? (
            <p className="py-4 text-sm text-ash">{t("integrations.empty")}</p>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export function JiraPanel({ workspaceId }: { workspaceId: string }) {
  const { t } = useI18n();
  const toast = useToast();
  const integrations = useIntegrations(workspaceId);
  const authorize = useJiraAuthorize(workspaceId);
  const jira = (integrations.data ?? []).filter((item) => item.provider === "JIRA");

  return (
    <section className="grid gap-6">
      <div className="sec-head">
        <div>
          <p className="kicker">{t("integrations.title")}</p>
          <h2 className="text-2xl">{t("integrations.jira")}</h2>
        </div>
        {jira.length === 0 ? (
          <Button
            disabled={authorize.isPending}
            onClick={() => {
              authorize.mutate(undefined, {
                onSuccess: (result) => {
                  window.location.assign(result.authorize_url);
                },
                onError: (error) => {
                  toast.pushError(error);
                },
              });
            }}
          >
            {t("integrations.connect")}
          </Button>
        ) : null}
      </div>
      <p className="lede">{t("integrations.jiraHint")}</p>
      {jira.length === 0 ? (
        <EmptyState title={t("integrations.empty")} hint={t("integrations.jiraHint")} />
      ) : (
        jira.map((integration) => (
          <ConnectedJira key={integration.id} integration={integration} workspaceId={workspaceId} />
        ))
      )}
    </section>
  );
}
