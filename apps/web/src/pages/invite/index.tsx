import { useEffect, useRef } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useAcceptInvite } from "@/entities/member/api";
import { useSession } from "@/entities/session";
import { RegisterForm } from "@/features/auth/ui/register-form";
import { LanguageSwitch } from "@/features/shell/ui/language-switch";
import { ThemeToggle } from "@/features/shell/ui/theme-toggle";
import { useI18n } from "@/shared/i18n";
import { useToast } from "@/shared/ui/toast";

export function InvitePage() {
  const { t } = useI18n();
  const toast = useToast();
  const navigate = useNavigate();
  const { token } = useParams<{ token: string }>();
  const { status } = useSession();
  const accept = useAcceptInvite();
  const started = useRef(false);

  useEffect(() => {
    if (status !== "authenticated" || !token || started.current) {
      return;
    }
    started.current = true;
    accept.mutate(token, {
      onSuccess: (result) => {
        void navigate(`/w/${result.workspace.slug}`, { replace: true });
      },
      onError: (error) => {
        toast.pushError(error);
      },
    });
  }, [accept, navigate, status, t, toast, token]);

  if (status === "booting") {
    return (
      <main className="shell grid min-h-screen place-content-center">
        <p className="mono text-ash">{t("common.loading")}…</p>
      </main>
    );
  }

  if (status === "authenticated") {
    return (
      <main className="shell grid min-h-screen place-content-center gap-4 text-center">
        <p className="kicker">{t("members.inviteTitle")}</p>
        <h1 className="text-3xl">{t("invite.accepting")}</h1>
        {accept.isError ? (
          <Link to="/" className="pill mx-auto">
            {t("common.back")}
          </Link>
        ) : null}
      </main>
    );
  }

  return (
    <main className="shell flex min-h-screen flex-col">
      <header className="bar stuck">
        <div className="shell bar-in justify-end">
          <LanguageSwitch />
          <ThemeToggle />
        </div>
      </header>
      <div className="mx-auto grid w-full max-w-md flex-1 content-center gap-8 py-24">
        <div className="grid gap-3">
          <p className="kicker">{t("members.inviteTitle")}</p>
          <h1 className="text-4xl">
            <span className="line on">
              <span>{t("invite.needAccount")}</span>
            </span>
          </h1>
          <p className="mono text-ash">{t("invite.expiresHint")}</p>
        </div>
        <RegisterForm inviteToken={token} redirectTo={`/invite/${token ?? ""}`} />
        <p className="text-sm text-ash">
          {t("invite.alreadyHave")}{" "}
          <Link to="/login" className="plain">
            {t("auth.signIn")}
          </Link>
        </p>
      </div>
    </main>
  );
}
