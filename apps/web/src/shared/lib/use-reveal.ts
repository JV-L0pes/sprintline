import { useEffect } from "react";

const REVEAL_SELECTOR = ".fade, .line";

/**
 * Revela elementos com .fade/.line quando entram na viewport (padrao do
 * portfolio). Sem observer/JS, um timeout de seguranca revela tudo.
 */
export function useReveal(deps: unknown[] = []): void {
  useEffect(() => {
    const nodes = Array.from(document.querySelectorAll<HTMLElement>(REVEAL_SELECTOR));
    if (nodes.length === 0) {
      return;
    }
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      for (const node of nodes) {
        node.classList.add("on");
      }
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            const target = entry.target as HTMLElement;
            const siblings = Array.from(target.parentElement?.children ?? []).filter(
              (el): el is HTMLElement => el instanceof HTMLElement && el.matches(REVEAL_SELECTOR),
            );
            const index = Math.min(siblings.indexOf(target), 5);
            target.style.transitionDelay = `${Math.max(0, index) * 90}ms`;
            const spans = target.querySelectorAll<HTMLElement>(".line > span");
            spans.forEach((span, spanIndex) => {
              span.style.transitionDelay = `${Math.max(0, index) * 90 + spanIndex * 110}ms`;
            });
            target.classList.add("on");
            observer.unobserve(target);
          }
        }
      },
      { threshold: 0.12, rootMargin: "0px 0px -6% 0px" },
    );
    for (const node of nodes) {
      observer.observe(node);
    }
    const safety = window.setTimeout(() => {
      for (const node of nodes) {
        node.classList.add("on");
      }
      observer.disconnect();
    }, 2000);
    return () => {
      window.clearTimeout(safety);
      observer.disconnect();
    };
    // deps controlam a re-observacao dos elementos quando a lista muda
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
}
