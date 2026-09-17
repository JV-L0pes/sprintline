import type { ReactNode } from "react";
import { cn } from "@/shared/lib/cn";

export function Badge({
  children,
  tone = "neutral",
  className,
}: {
  children: ReactNode;
  tone?: "neutral" | "live" | "danger";
  className?: string;
}) {
  const tones = {
    neutral: "border-rule text-ash",
    live: "border-gold text-gold",
    danger: "border-danger text-danger",
  } as const;
  return (
    <span
      className={cn(
        "mono inline-flex items-center border px-1.5 py-0.5 tracking-[0.1em]",
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

export function LiveDot({ muted = false }: { muted?: boolean }) {
  return (
    <span className={cn("live", muted && "muted")}>
      <i aria-hidden />
    </span>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return (
    <span
      className={cn("block animate-pulse bg-hover", className)}
      style={{ minHeight: "0.9rem" }}
      aria-hidden
    />
  );
}

export function Avatar({ name }: { name: string }) {
  const initials = name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join("");
  return (
    <span className="avatar" title={name}>
      {initials}
    </span>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="empty">
      <p className="font-semibold text-ink">{title}</p>
      {hint ? <p className="mt-1">{hint}</p> : null}
    </div>
  );
}

export function Meter({
  value,
  max,
  gold = false,
}: {
  value: number;
  max: number;
  gold?: boolean;
}) {
  const percentage = max <= 0 ? 0 : Math.min(100, Math.round((value / max) * 100));
  return (
    <div className={cn("meter", gold && "gold")} role="presentation">
      <i style={{ width: `${String(percentage)}%` }} />
    </div>
  );
}
