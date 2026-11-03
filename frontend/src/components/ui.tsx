import { AlertCircle, Award, CheckCircle2, Loader2, LucideIcon } from "lucide-react";
import { ReactNode } from "react";

import { NewBadge } from "../api/assessments";

export function Spinner({ label = "Loading..." }: { label?: string }) {
  return (
    <p className="flex items-center gap-2 py-6 text-sm text-navy/60">
      <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
      {label}
    </p>
  );
}

export function Alert({ kind = "error", children }: { kind?: "error" | "success" | "info"; children: ReactNode }) {
  const styles = {
    error: "border-red-200 bg-red-50 text-red-700",
    success: "border-green-200 bg-green-50 text-green-800",
    info: "border-gold/40 bg-gold/10 text-navy/80",
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
      <p className="font-semibold text-navy">{title}</p>
      {children && <div className="mt-1 max-w-sm text-sm text-navy/60">{children}</div>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function StatTile({ label, value, icon: Icon }: { label: string; value: ReactNode; icon?: LucideIcon }) {
  return (
    <div className="card p-3">
      <div className="flex items-center gap-1.5 text-xs font-medium text-navy/55">
        {Icon && <Icon className="h-3.5 w-3.5" aria-hidden />}
        {label}
      </div>
      <p className="mt-1 text-2xl font-bold tracking-tight text-navy">{value}</p>
    </div>
  );
}

export function NewBadges({ badges }: { badges: NewBadge[] }) {
  if (badges.length === 0) return null;
  return (
    <div className="animate-pop rounded-xl border border-gold bg-gradient-to-br from-gold/20 to-gold/5 p-3">
      <p className="flex items-center gap-1.5 text-sm font-bold text-navy">
        <Award className="h-4 w-4 text-gold-dark" aria-hidden />
        Badge{badges.length === 1 ? "" : "s"} earned
      </p>
      <ul className="mt-1.5 space-y-1">
        {badges.map((badge) => (
          <li key={badge.code} className="text-sm text-navy/80">
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
    gold: "bg-gold/25 text-navy",
    red: "bg-red-100 text-red-700",
    grey: "bg-navy/10 text-navy/70",
    blue: "bg-sky-100 text-sky-800",
  }[tone];
  return <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ${styles}`}>{children}</span>;
}
