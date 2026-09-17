import { useEffect, useMemo, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useConnectTrello } from "@/entities/integration/api";
import {
  parseTrelloToken,
  TRELLO_CONSUMED_KEY,
  TRELLO_PENDING_KEY,
} from "@/entities/integration/model";
import { useI18n } from "@/shared/i18n";

interface PendingConnect {
  workspaceId: string;
  slug: string;
}

export function TrelloCallbackPage() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const token = parseTrelloToken(window.location.hash);
  const pending = useMemo<PendingConnect | null>(() => {
    try {
      return JSON.parse(
        sessionStorage.getItem(TRELLO_PENDING_KEY) ?? "null",
      ) as PendingConnect | null;
    } catch {
      return null;
    }
  }, []);
  const connect = useConnectTrello(pending?.workspaceId ?? "");
  const started = useRef(false);

  useEffect(() => {
    if (started.current) {
      return;
    }
    started.current = true;
    if (!pending || !token) {
      void navigate("/", { replace: true });
      return;
    }
    if (sessionStorage.getItem(TRELLO_CONSUMED_KEY) === token) {
      void navigate(`/w/${pending.slug}/settings?trello=connected`, { replace: true });
      return;
    }
    sessionStorage.setItem(TRELLO_CONSUMED_KEY, token);
    connect.mutate(token, {
      onSuccess: () => {
        sessionStorage.removeItem(TRELLO_PENDING_KEY);
        void navigate(`/w/${pending.slug}/settings?trello=connected`, { replace: true });
      },
      onError: () => {
        void navigate(`/w/${pending.slug}/settings?trello=error`, { replace: true });
      },
    });
  }, [connect, navigate, pending, token]);

  return (
    <main className="shell grid min-h-screen place-content-center gap-6 text-center">
      <p className="kicker">{t("integrations.trello")}</p>
      <h1 className="text-3xl">
        {connect.isPending || connect.isIdle
          ? t("common.loading")
          : connect.isError
            ? t("integrations.callbackError")
            : t("integrations.callbackConnected")}
      </h1>
      <Link to="/" className="pill mx-auto">
        {t("common.confirm")}
      </Link>
    </main>
  );
}
