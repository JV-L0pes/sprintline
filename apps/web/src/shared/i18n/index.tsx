import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { en, pt } from "./messages";

export type Language = "pt-BR" | "en";

const DICTIONARIES: Record<Language, Record<string, unknown>> = {
  "pt-BR": pt,
  en: en,
};

const STORAGE_KEY = "cadencia-lang";

interface I18nValue {
  language: Language;
  setLanguage: (language: Language) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
}

const I18nContext = createContext<I18nValue | null>(null);

function resolve(dictionary: Record<string, unknown>, key: string): string | undefined {
  const segments = key.split(".");
  let current: unknown = dictionary;
  for (const segment of segments) {
    if (typeof current !== "object" || current === null) {
      return undefined;
    }
    current = (current as Record<string, unknown>)[segment];
  }
  return typeof current === "string" ? current : undefined;
}

function interpolate(template: string, params?: Record<string, string | number>): string {
  if (!params) {
    return template;
  }
  return template.replace(/\{(\w+)\}/g, (match, name: string) => {
    const value = params[name];
    return value === undefined ? match : String(value);
  });
}

function initialLanguage(): Language {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved === "pt-BR" || saved === "en") {
    return saved;
  }
  return navigator.language.toLowerCase().startsWith("en") ? "en" : "pt-BR";
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(initialLanguage);

  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);

  const setLanguage = useCallback((next: Language) => {
    localStorage.setItem(STORAGE_KEY, next);
    setLanguageState(next);
  }, []);

  const t = useCallback(
    (key: string, params?: Record<string, string | number>) => {
      const template =
        resolve(DICTIONARIES[language], key) ?? resolve(DICTIONARIES["pt-BR"], key) ?? key;
      return interpolate(template, params);
    },
    [language],
  );

  const value = useMemo(() => ({ language, setLanguage, t }), [language, setLanguage, t]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nValue {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error("useI18n deve ser usado dentro de I18nProvider");
  }
  return context;
}

export function translateErrorCode(
  t: (key: string) => string,
  code: string | undefined,
  detail?: string,
): string {
  if (code) {
    const known = t(`errors.${code}`);
    if (known !== `errors.${code}`) {
      return known;
    }
  }
  return detail ?? t("errors.generic");
}
