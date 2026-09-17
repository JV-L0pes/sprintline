import { type Language, useI18n } from "@/shared/i18n";

const OPTIONS: { value: Language; label: string }[] = [
  { value: "pt-BR", label: "PT" },
  { value: "en", label: "EN" },
];

export function LanguageSwitch() {
  const { language, setLanguage } = useI18n();
  return (
    <div className="seg" role="group" aria-label="Idioma / Language">
      {OPTIONS.map((option) => (
        <button
          key={option.value}
          type="button"
          aria-pressed={language === option.value}
          onClick={() => {
            setLanguage(option.value);
          }}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
