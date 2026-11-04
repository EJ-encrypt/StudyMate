import { AlertCircle, CheckCircle2, Info, X } from "lucide-react";
import { useEffect, useState } from "react";

import { dismiss, subscribe, Toast } from "../lib/toast";

const ICONS = { success: CheckCircle2, error: AlertCircle, info: Info };
const ICON_COLOURS = { success: "text-green-400", error: "text-red-400", info: "text-gold" };

/** Where toasts appear: above the phone tab bar, bottom right on a computer. */
export default function Toaster() {
  const [toasts, setToasts] = useState<Toast[]>([]);
  useEffect(() => subscribe(setToasts), []);

  return (
    <div
      aria-live="polite"
      className="pointer-events-none fixed inset-x-0 bottom-20 z-50 flex flex-col items-center gap-2 px-4 md:bottom-6 md:right-6 md:left-auto md:items-end"
    >
      {toasts.map((toast) => {
        const Icon = ICONS[toast.kind];
        return (
          <div
            key={toast.id}
            role={toast.kind === "error" ? "alert" : "status"}
            className="pointer-events-auto flex w-full max-w-sm animate-fade-in items-center gap-3 rounded-xl bg-navy-dark px-4 py-3 text-sm text-white shadow-lift"
          >
            <Icon className={`h-4 w-4 shrink-0 ${ICON_COLOURS[toast.kind]}`} aria-hidden />
            <span className="min-w-0 flex-1">{toast.text}</span>
            {toast.action && (
              <button type="button" onClick={toast.action.onClick} className="shrink-0 font-bold text-gold hover:underline">
                {toast.action.label}
              </button>
            )}
            <button type="button" onClick={() => dismiss(toast.id)} aria-label="Dismiss" className="shrink-0 text-white/50 hover:text-white">
              <X className="h-4 w-4" aria-hidden />
            </button>
          </div>
        );
      })}
    </div>
  );
}
