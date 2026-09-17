import { useState } from "react";
import {
  useDisconnectIntegration,
  useIntegrations,
  useJobs,
  useStartTrelloImport,
  useTrelloAuthorize,
  useTrelloBoards,
} from "@/entities/integration/api";
import type { Integration } from "@/shared/api/types";
import { useI18n } from "@/shared/i18n";
import { Button } from "@/shared/ui/button";
import { Select } from "@/shared/ui/input";
import { EmptyState } from "@/shared/ui/misc";
import { useToast } from "@/shared/ui/toast";
import { JobRow } from "./job-row";

const PENDING_KEY = "cadencia.trello.connect";

function ConnectedTrello({
  integration,
  workspaceId,
}: {
  integration: Integration;
  workspaceId: string;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const boards = useTrelloBoards(workspaceId, integration.id);
  const startImport = useStartTrelloImport(workspaceId, integration.id);
  const disconnect = useDisconnectIntegration(workspaceId);
  const jobs = useJobs(workspaceId, integration.id);
  const [boardId, setBoardId] = useState("");

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span className="live">
          <i aria-hidden /> {t("integrations.connected", { site: integration.site_url })}
        </span>
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
      <div className="flex items-end gap-3">
        <label className="field flex-1" htmlFor={`board-${integration.id}`}>
          <span className="lab">{t("integrations.trelloBoards")}</span>
          <Select
            id={`board-${integration.id}`}
            value={boardId}
            onChange={(event) => {
              setBoardId(event.target.value);
            }}
          >
            <option value="">{t("integrations.selectBoard")}</option>
            {(boards.data ?? []).map((board) => (
              <option key={board.id} value={board.id}>
                {board.name}
              </option>
            ))}
          </Select>
        </label>
        <Button
          disabled={startImport.isPending || boardId === ""}
          onClick={() => {
            startImport.mutate(boardId, {
              onError: (error) => {
                toast.pushError(error);
              },
            });
          }}
        >
          {t("integrations.importBoard")}
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

export function TrelloPanel({
  workspaceId,
  workspaceSlug,
}: {
  workspaceId: string;
  workspaceSlug: string;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const integrations = useIntegrations(workspaceId);
  const authorize = useTrelloAuthorize(workspaceId);
  const trello = (integrations.data ?? []).filter((item) => item.provider === "TRELLO");

  const connect = () => {
    authorize.mutate(undefined, {
      onSuccess: (result) => {
        sessionStorage.setItem(PENDING_KEY, JSON.stringify({ workspaceId, slug: workspaceSlug }));
        window.location.assign(result.authorize_url);
      },
      onError: (error) => {
        toast.pushError(error);
      },
    });
  };

  return (
    <section className="grid gap-6">
      <div className="sec-head">
        <div>
          <p className="kicker">{t("integrations.title")}</p>
          <h2 className="text-2xl">{t("integrations.trello")}</h2>
        </div>
        {trello.length === 0 ? (
          <Button disabled={authorize.isPending} onClick={connect}>
            {t("integrations.connectTrello")}
          </Button>
        ) : null}
      </div>
      <p className="lede">{t("integrations.trelloHint")}</p>
      {trello.length === 0 ? (
        <EmptyState title={t("integrations.empty")} hint={t("integrations.trelloHint")} />
      ) : (
        trello.map((integration) => (
          <ConnectedTrello
            key={integration.id}
            integration={integration}
            workspaceId={workspaceId}
          />
        ))
      )}
    </section>
  );
}
