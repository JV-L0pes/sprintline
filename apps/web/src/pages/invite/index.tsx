import { Link, useNavigate, useParams } from "react-router-dom";
import { useAcceptInvite } from "@/entities/member/api";
import { useSession } from "@/entities/session";
import { useI18n } from "@/shared/i18n";
import { Button } from "@/shared/ui/button";
import { useToast } from "@/shared/ui/toast";

export function InvitePage() {
  const { t } = useI18n();
  const toast = useToast();
  const navigate = useNavigate();
  const { token } = useParams<{ token: string }>();
  const { status } = useSession();
  const accept = useAcceptInvite();

  if (status !== "authenticated") {
    return (
      <main className="shell grid min-h-screen place-content-center gap-6 text-center">
        <h1 className="text-3xl">{t("members.inviteTitle")}</h1>
        <p className="lede mx-auto max-w-md">{t("members.inviteHint")}</p>
        <div className="flex justify-center gap-4">
          <Link to="/register" className="pill">
            {t("auth.signUp")}
          </Link>
          <Link to="/login" className="plain">
            {t("auth.signIn")}
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="shell grid min-h-screen place-content-center gap-6 text-center">
      <h1 className="text-3xl">{t("members.inviteTitle")}</h1>
      <Button
        disabled={accept.isPending}
        onClick={() => {
          if (!token) {
            toast.pushError(new Error("missing token"));
            return;
          }
          accept.mutate(token, {
            onSuccess: (result) => {
              void navigate(`/w/${result.workspace.slug}`);
            },
            onError: (error) => {
              toast.pushError(error);
            },
          });
        }}
      >
        {t("common.confirm")}
      </Button>
    </main>
  );
}
