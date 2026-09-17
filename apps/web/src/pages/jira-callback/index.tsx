import { useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useI18n } from "@/shared/i18n";

export function JiraCallbackPage() {
  const { t } = useI18n();
  const [params] = useSearchParams();
  const status = params.get("status");
  const error = status !== "connected";

  useEffect(() => {
    document.title = "Cadencia — Jira";
  }, []);

  return (
    <main className="shell grid min-h-screen place-content-center gap-6 text-center">
      <p className="kicker">{t("integrations.jira")}</p>
      <h1 className="text-3xl">
        {error ? t("integrations.callbackError") : t("integrations.callbackConnected")}
      </h1>
      <Link to="/" className="pill mx-auto">
        {t("common.confirm")}
      </Link>
    </main>
  );
}
