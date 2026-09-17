import { SunMoon } from "lucide-react";
import { useRef } from "react";
import { useI18n } from "@/shared/i18n";
import { useTheme } from "@/shared/lib/theme";

export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const { language } = useI18n();
  const ref = useRef<HTMLButtonElement>(null);
  const label =
    theme === "dark"
      ? language === "pt-BR"
        ? "Ativar modo claro"
        : "Switch to light mode"
      : language === "pt-BR"
        ? "Ativar modo escuro"
        : "Switch to dark mode";
  return (
    <button
      ref={ref}
      type="button"
      className="sq"
      aria-pressed={theme === "dark"}
      aria-label={label}
      onClick={() => {
        toggle(ref.current);
      }}
    >
      <SunMoon size={15} strokeWidth={2} aria-hidden />
    </button>
  );
}
