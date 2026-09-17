import { createContext, type ReactNode, useCallback, useContext, useMemo, useState } from "react";

type Theme = "light" | "dark";

interface ThemeContextValue {
  theme: Theme;
  toggle: (origin?: HTMLElement | null) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);
const STORAGE_KEY = "cadencia-theme";

function currentTheme(): Theme {
  const attribute = document.documentElement.getAttribute("data-theme");
  return attribute === "dark" ? "dark" : "light";
}

function prefersReducedMotion(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(currentTheme);

  const apply = useCallback((next: Theme) => {
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem(STORAGE_KEY, next);
    setTheme(next);
  }, []);

  const toggle = useCallback(
    (origin?: HTMLElement | null) => {
      const next: Theme = theme === "dark" ? "light" : "dark";
      const supportsViewTransition = "startViewTransition" in document;
      if (!supportsViewTransition || prefersReducedMotion() || !origin) {
        apply(next);
        return;
      }
      const rect = origin.getBoundingClientRect();
      const x = rect.left + rect.width / 2;
      const y = rect.top + rect.height / 2;
      const radius = Math.hypot(
        Math.max(x, window.innerWidth - x),
        Math.max(y, window.innerHeight - y),
      );
      const transition = (
        document as Document & {
          startViewTransition: (callback: () => void) => { ready: Promise<void> };
        }
      ).startViewTransition(() => {
        apply(next);
      });
      document.documentElement.classList.add("theme-swapping");
      void transition.ready
        .then(() => {
          document.documentElement.animate(
            {
              clipPath: [
                `circle(0px at ${x.toString()}px ${y.toString()}px)`,
                `circle(${(radius * 1.25).toString()}px at ${x.toString()}px ${y.toString()}px)`,
              ],
            },
            {
              duration: Math.round(radius * 0.4),
              easing: "linear",
              pseudoElement: "::view-transition-new(root)",
            },
          );
        })
        .finally(() => {
          document.documentElement.classList.remove("theme-swapping");
        });
    },
    [apply, theme],
  );

  const value = useMemo(() => ({ theme, toggle }), [theme, toggle]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme deve ser usado dentro de ThemeProvider");
  }
  return context;
}
