import { LoginForm } from "@/features/auth/ui/login-form";
import { LanguageSwitch } from "@/features/shell/ui/language-switch";
import { ThemeToggle } from "@/features/shell/ui/theme-toggle";
import { useI18n } from "@/shared/i18n";

export function LoginPage() {
  const { t } = useI18n();
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
          <p className="kicker">{t("common.appName")}</p>
          <h1 className="text-4xl">
            <span className="line on">
              <span>{t("auth.loginTitle")}</span>
            </span>
          </h1>
          <p className="lede">{t("common.tagline")}</p>
        </div>
        <LoginForm />
      </div>
    </main>
  );
}
