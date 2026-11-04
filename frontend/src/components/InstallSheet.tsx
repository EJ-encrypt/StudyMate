import { BellRing, Plus, Share, X } from "lucide-react";
import { useEffect, useRef } from "react";

import { hideInstallHelp, useInstallHelpOpen } from "../lib/installHelp";

const STEPS = [
  { icon: Share, text: "In Safari, tap the Share button at the bottom of the screen." },
  { icon: Plus, text: "Scroll down and choose Add to Home Screen, then Add." },
  { icon: BellRing, text: "Open StudyMate from its new icon and turn on notifications from there." },
];

/**
 * Pops up over everything, so it is seen wherever the switch was tapped:
 * iPhones only let a web app send notifications once it is on the Home Screen.
 */
export default function InstallSheet() {
  const isOpen = useInstallHelpOpen();
  const sheet = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    sheet.current?.focus();
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && hideInstallHelp();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isOpen]);

  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-[70] flex items-end justify-center bg-navy-dark/60 p-3 sm:items-center" onClick={hideInstallHelp}>
      <div
        ref={sheet}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-labelledby="install-title"
        onClick={(event) => event.stopPropagation()}
        className="card pb-safe w-full max-w-md animate-fade-in p-5 focus:outline-none"
      >
        <div className="flex items-start justify-between gap-3">
          <h2 id="install-title" className="text-lg font-bold text-ink">
            Add StudyMate to your Home Screen first
          </h2>
          <button type="button" onClick={hideInstallHelp} aria-label="Close" className="btn-ghost -mr-2 -mt-1 p-1.5">
            <X className="h-4 w-4" aria-hidden />
          </button>
        </div>
        <p className="mt-1 text-sm text-ink/65">
          On an iPhone or iPad, notifications only work for StudyMate once it is saved to your Home Screen. It takes
          a few seconds:
        </p>
        <ol className="mt-4 space-y-3">
          {STEPS.map(({ icon: Icon, text }, index) => (
            <li key={text} className="flex items-start gap-3 text-sm text-ink">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-navy text-gold">
                <Icon className="h-4 w-4" aria-hidden />
              </span>
              <span className="pt-1.5">
                <span className="font-semibold">{index + 1}.</span> {text}
              </span>
            </li>
          ))}
        </ol>
        <button type="button" onClick={hideInstallHelp} className="btn-primary mt-5 w-full py-2.5">
          Got it
        </button>
      </div>
    </div>
  );
}
