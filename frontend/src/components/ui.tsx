import { AlertCircle, Award, CheckCircle2, Loader2, LucideIcon } from "lucide-react";
import { ReactNode } from "react";

import { NewBadge } from "../api/assessments";

export function Spinner({ label = "Loading..." }: { label?: string }) {
  return (
    <p className="flex items-center gap-2 py-6 text-sm text-ink/60">
      <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
      {label}
    </p>
  );
}

export function Alert({ kind = "error", children }: { kind?: "error" | "success" | "info"; children: ReactNode }) {
  const styles = {
    error: "border-red-200 bg-red-50 text-red-700",
    success: "border-green-200 bg-green-50 text-green-800",
    info: "border-gold/40 bg-gold/10 text-ink/80",
  }[kind];
  const Icon = kind === "success" ? CheckCircle2 : AlertCircle;
  return (
    <div role={kind === "error" ? "alert" : "status"} className={`flex items-start gap-2 rounded-lg border px-3 py-2 text-sm ${styles}`}>
      <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
      <div>{children}</div>
    </div>
  );
}

export function EmptyState({
  icon: Icon,
  title,
  children,
  action,
}: {
  icon: LucideIcon;
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="card flex flex-col items-center px-6 py-10 text-center">
      <span className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-gold/15 text-gold-dark">
        <Icon className="h-6 w-6" aria-hidden />
      </span>
      <p className="font-semibold text-ink">{title}</p>
      {children && <div className="mt-1 max-w-sm text-sm text-ink/60">{children}</div>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export type StatTone = "plain" | "fire" | "amber" | "violet" | "sky";

// A tinted tile, a coloured label, and an icon badge per tone. Dark mode
// swaps the pale tints for deep ones (index.css).
const TONES: Record<StatTone, { tile: string; label: string; badge: string; icon: string }> = {
  plain: { tile: "card", label: "text-ink/55", badge: "", icon: "" },
  fire: {
    tile: "rounded-xl border border-red-200 bg-red-50 shadow-card",
    label: "text-red-700",
    badge: "bg-gradient-to-br from-amber-100 to-red-100",
    // Filled orange inside a red outline: reads as a flame, not a line drawing.
    icon: "fill-orange-400 text-red-500",
  },
  amber: {
    tile: "rounded-xl border border-amber-200 bg-amber-50 shadow-card",
    label: "text-amber-700",
    badge: "bg-amber-100",
    icon: "fill-amber-300 text-amber-600",
  },
  violet: {
    tile: "rounded-xl border border-violet-200 bg-violet-50 shadow-card",
    label: "text-violet-700",
    badge: "bg-violet-100",
    icon: "fill-violet-200 text-violet-600",
  },
  sky: {
    tile: "rounded-xl border border-sky-200 bg-sky-50 shadow-card",
    label: "text-sky-700",
    badge: "bg-sky-100",
    icon: "text-sky-600",
  },
};

export function StatTile({
  label,
  value,
  icon: Icon,
  tone = "plain",
}: {
  label: string;
  value: ReactNode;
  icon?: LucideIcon;
  tone?: StatTone;
}) {
  const style = TONES[tone];
  return (
    <div className={`${style.tile} p-3`}>
      <div className={`flex items-center gap-1.5 text-xs font-semibold ${style.label}`}>
        {Icon &&
          (tone === "plain" ? (
            <Icon className="h-3.5 w-3.5" aria-hidden />
          ) : (
            <span className={`flex h-6 w-6 items-center justify-center rounded-full ${style.badge}`}>
              <Icon className={`h-4 w-4 ${style.icon}`} aria-hidden />
            </span>
          ))}
        {label}
      </div>
      <p className="mt-1.5 text-2xl font-bold tracking-tight tabular-nums text-ink">{value}</p>
    </div>
  );
}

export function NewBadges({ badges }: { badges: NewBadge[] }) {
  if (badges.length === 0) return null;
  return (
    <div className="animate-pop rounded-xl border border-gold bg-gradient-to-br from-gold/20 to-gold/5 p-3">
      <p className="flex items-center gap-1.5 text-sm font-bold text-ink">
        <Award className="h-4 w-4 text-gold-dark" aria-hidden />
        Badge{badges.length === 1 ? "" : "s"} earned
      </p>
      <ul className="mt-1.5 space-y-1">
        {badges.map((badge) => (
          <li key={badge.code} className="text-sm text-ink/80">
            <span className="font-semibold">{badge.name}</span> — {badge.description}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function StatusPill({ tone, children }: { tone: "green" | "gold" | "red" | "grey" | "blue"; children: ReactNode }) {
  const styles = {
    green: "bg-green-100 text-green-800",
    gold: "bg-gold/25 text-ink",
    red: "bg-red-100 text-red-700",
    grey: "bg-ink/10 text-ink/70",
    blue: "bg-sky-100 text-sky-800",
  }[tone];
  return <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ${styles}`}>{children}</span>;
}
