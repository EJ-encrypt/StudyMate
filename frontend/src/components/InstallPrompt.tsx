import { Download, Share, X } from "lucide-react";
import { useEffect, useState } from "react";

import { isIos, isStandalone } from "../lib/push";

const DISMISSED_KEY = "studymate-install-dismissed";
const QUIET_DAYS = 14;

/** Chrome's install event; not in TypeScript's DOM types. */
interface InstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

function recentlyDismissed(): boolean {
  try {
    const at = Number(localStorage.getItem(DISMISSED_KEY) ?? 0);
    return Date.now() - at < QUIET_DAYS * 24 * 60 * 60 * 1000;
  } catch {
    return false;
  }
}

/**
 * "Add StudyMate to your home screen". Android and desktop Chrome offer a
 * real install button; on an iPhone the only way is Share, Add to Home Screen,
 * which is also what lets lecture reminders reach it.
 */
export default function InstallPrompt() {
  const [installEvent, setInstallEvent] = useState<InstallPromptEvent | null>(null);
  const [showIosHint, setShowIosHint] = useState(false);
  const [isHidden, setIsHidden] = useState(() => isStandalone() || recentlyDismissed());

  useEffect(() => {
    if (isHidden) return;
    const onPrompt = (event: Event) => {
      event.preventDefault();
      setInstallEvent(event as InstallPromptEvent);
    };
    window.addEventListener("beforeinstallprompt", onPrompt);
    // Safari on iPhone has no install event; show the steps instead.
    if (isIos()) setShowIosHint(true);
    return () => window.removeEventListener("beforeinstallprompt", onPrompt);
  }, [isHidden]);

  function dismiss() {
    try {
      localStorage.setItem(DISMISSED_KEY, String(Date.now()));
    } catch {
      // Private browsing: it simply shows again next visit.
    }
    setIsHidden(true);
  }

  async function install() {
    if (!installEvent) return;
    await installEvent.prompt();
    await installEvent.userChoice.catch(() => undefined);
    setInstallEvent(null);
    setIsHidden(true);
  }

  if (isHidden || (!installEvent && !showIosHint)) return null;

  return (
    <div className="mb-4 flex items-start gap-3 rounded-xl border border-gold/50 bg-gold/10 p-3 text-sm">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-navy text-gold">
        <Download className="h-4 w-4" aria-hidden />
      </span>
      <div className="min-w-0 flex-1">
        <p className="font-semibold text-ink">Add StudyMate to your home screen</p>
        {installEvent ? (
          <p className="text-ink/65">It opens like an app, full screen, and lecture reminders reach you.</p>
        ) : (
          <p className="text-ink/65">
            Tap <Share className="inline h-3.5 w-3.5 -translate-y-px" aria-label="Share" /> in Safari, then{" "}
            <span className="font-semibold text-ink">Add to Home Screen</span>. iPhones only deliver lecture reminders to
            apps added this way.
          </p>
        )}
        {installEvent && (
          <button type="button" onClick={() => void install()} className="btn-primary mt-2 px-3 py-1.5 text-xs">
            Install
          </button>
        )}
      </div>
      <button type="button" onClick={dismiss} aria-label="Not now" className="btn-ghost -mr-1 -mt-1 p-1.5">
        <X className="h-4 w-4" aria-hidden />
      </button>
    </div>
  );
}
