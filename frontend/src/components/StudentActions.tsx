import { Ban, Flag, MoreHorizontal } from "lucide-react";
import { FormEvent, useEffect, useRef, useState } from "react";

import { errorMessage } from "../api/client";
import { blockStudent, reportStudent, ReportReason } from "../api/social";
import { toast } from "../lib/toast";
import { Alert } from "./ui";

const REASONS: [ReportReason, string][] = [
  ["username", "Offensive name or username"],
  ["harassment", "Harassment or bullying"],
  ["spam", "Spam or unwanted requests"],
  ["other", "Something else"],
];

function ReportDialog({ name, studentId, onClose, onDone }: { name: string; studentId: string; onClose: () => void; onDone: () => void }) {
  const [reason, setReason] = useState<ReportReason>("username");
  const [details, setDetails] = useState("");
  const [alsoBlock, setAlsoBlock] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);
  const dialog = useRef<HTMLDivElement>(null);

  useEffect(() => {
    dialog.current?.focus();
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function send(event: FormEvent) {
    event.preventDefault();
    setIsSending(true);
    setError(null);
    try {
      await reportStudent(studentId, reason, details, alsoBlock);
      toast(alsoBlock ? `Thanks. ${name} is reported and blocked.` : `Thanks. ${name} is reported.`);
      onDone();
    } catch (err) {
      setError(errorMessage(err, "Could not send that report."));
      setIsSending(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-navy-dark/60 p-4 sm:items-center" onClick={onClose}>
      <div
        ref={dialog}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-labelledby="report-title"
        onClick={(event) => event.stopPropagation()}
        className="card w-full max-w-md animate-fade-in p-5 focus:outline-none"
      >
        <h2 id="report-title" className="text-lg font-bold text-ink">
          Report {name}
        </h2>
        <p className="mt-1 text-sm text-ink/60">Reports are private. {name} is not told who sent one.</p>
        <form onSubmit={send} className="mt-4 space-y-3">
          <fieldset className="space-y-1.5">
            <legend className="label mb-1">What is wrong?</legend>
            {REASONS.map(([value, label]) => (
              <label key={value} className="flex items-center gap-2 text-sm text-ink">
                <input type="radio" name="reason" checked={reason === value} onChange={() => setReason(value)} className="accent-navy" />
                {label}
              </label>
            ))}
          </fieldset>
          <label className="block">
            <span className="label">More detail (optional)</span>
            <textarea value={details} onChange={(e) => setDetails(e.target.value)} maxLength={1000} rows={3} className="input mt-1" />
          </label>
          <label className="flex items-center gap-2 text-sm text-ink">
            <input type="checkbox" checked={alsoBlock} onChange={(e) => setAlsoBlock(e.target.checked)} className="accent-navy" />
            Also block {name}
          </label>
          {error && <Alert>{error}</Alert>}
          <div className="flex justify-end gap-2">
            <button type="button" onClick={onClose} className="btn-ghost">
              Cancel
            </button>
            <button type="submit" disabled={isSending} className="btn-danger">
              <Flag className="h-4 w-4" aria-hidden /> {isSending ? "Sending..." : "Send report"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/** The "..." menu beside another student: report or block them. */
export default function StudentActions({ studentId, name, onChanged }: { studentId: string; name: string; onChanged: () => void }) {
  const [isOpen, setIsOpen] = useState(false);
  const [isReporting, setIsReporting] = useState(false);
  const menu = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    const close = (event: MouseEvent) => {
      if (!menu.current?.contains(event.target as Node)) setIsOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [isOpen]);

  async function block() {
    setIsOpen(false);
    if (!window.confirm(`Block ${name}? They will not be able to find you, add you or challenge you. They are not told.`)) return;
    try {
      await blockStudent(studentId);
      toast(`${name} is blocked. You can unblock them in Settings, Privacy.`);
      onChanged();
    } catch (err) {
      toast(errorMessage(err, "Could not block them."), { kind: "error" });
    }
  }

  return (
    <div ref={menu} className="relative">
      <button
        type="button"
        onClick={() => setIsOpen((open) => !open)}
        aria-label={`More options for ${name}`}
        aria-expanded={isOpen}
        className="btn-ghost p-1.5 text-ink/40"
      >
        <MoreHorizontal className="h-4 w-4" aria-hidden />
      </button>
      {isOpen && (
        <div role="menu" className="card absolute right-0 top-full z-20 mt-1 w-40 animate-fade-in overflow-hidden py-1 shadow-lift">
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              setIsOpen(false);
              setIsReporting(true);
            }}
            className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-ink hover:bg-ink/5"
          >
            <Flag className="h-4 w-4" aria-hidden /> Report
          </button>
          <button type="button" role="menuitem" onClick={() => void block()} className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-red-600 hover:bg-ink/5">
            <Ban className="h-4 w-4" aria-hidden /> Block
          </button>
        </div>
      )}
      {isReporting && (
        <ReportDialog
          name={name}
          studentId={studentId}
          onClose={() => setIsReporting(false)}
          onDone={() => {
            setIsReporting(false);
            onChanged();
          }}
        />
      )}
    </div>
  );
}
