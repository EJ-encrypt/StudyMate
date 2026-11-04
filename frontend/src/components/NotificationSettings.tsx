import { BellOff, BellRing, Mail, Send, Smartphone } from "lucide-react";
import { useEffect, useState } from "react";

import { updatePreferences } from "../api/auth";
import { errorMessage } from "../api/client";
import { useAuth } from "../context/AuthContext";
import {
  NotificationConfig,
  PushState,
  disablePush,
  enablePush,
  getNotificationConfig,
  pushState,
  sendTestNotification,
} from "../lib/push";
import { Alert } from "./ui";

function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (value: boolean) => void; label: string }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={[
        "relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition",
        checked ? "bg-navy" : "bg-ink/20",
      ].join(" ")}
    >
      <span
        className={[
          "inline-block h-5 w-5 transform rounded-full bg-white shadow transition",
          checked ? "translate-x-5" : "translate-x-0.5",
        ].join(" ")}
      />
    </button>
  );
}

/** Lecture reminder channels: this device's push, and email. */
export default function NotificationSettings() {
  const { user, refresh } = useAuth();
  const [config, setConfig] = useState<NotificationConfig | null>(null);
  const [state, setState] = useState<PushState | null>(null);
  const [isBusy, setIsBusy] = useState(false);
  const [message, setMessage] = useState<{ kind: "success" | "error" | "info"; text: string } | null>(null);

  useEffect(() => {
    getNotificationConfig().then(setConfig).catch(() => undefined);
    pushState().then(setState).catch(() => setState("unsupported"));
  }, []);

  async function togglePush(on: boolean) {
    if (!config) return;
    setIsBusy(true);
    setMessage(null);
    try {
      const next = on ? await enablePush(config.vapid_public_key) : await disablePush();
      setState(next);
      if (on && next === "denied") {
        setMessage({ kind: "error", text: "Notifications are blocked. Allow them for this site in your browser settings." });
      }
      if (on && next === "on" && user && !user.notify_push) {
        await updatePreferences({ notify_push: true });
        await refresh();
      }
    } catch (err) {
      setMessage({ kind: "error", text: errorMessage(err, "Could not turn on notifications on this device.") });
    } finally {
      setIsBusy(false);
    }
  }

  async function toggleEmail(on: boolean) {
    await updatePreferences({ notify_email: on });
    await refresh();
  }

  async function test() {
    setIsBusy(true);
    setMessage(null);
    try {
      const sent = await sendTestNotification();
      const parts = [];
      if (sent.push) parts.push(`a notification to ${sent.push} device${sent.push === 1 ? "" : "s"}`);
      if (sent.email) parts.push(`an email to ${user?.email}`);
      setMessage(
        parts.length
          ? { kind: "success", text: `Sent ${parts.join(" and ")}.` }
          : { kind: "info", text: "Nothing was sent. Turn on at least one reminder channel above." },
      );
    } catch (err) {
      setMessage({ kind: "error", text: errorMessage(err, "Could not send a test.") });
    } finally {
      setIsBusy(false);
    }
  }

  const pushOn = state === "on";

  return (
    <div className="card divide-y divide-ink/5">
      <div className="flex items-start justify-between gap-4 p-4">
        <div className="flex gap-3">
          <Smartphone className="mt-0.5 h-5 w-5 shrink-0 text-ink/50" aria-hidden />
          <div>
            <p className="text-sm font-semibold text-ink">Notifications on this device</p>
            <p className="text-xs text-ink/60">
              {state === "needs-install" &&
                "On iPhone and iPad: tap Share, then Add to Home Screen, and open StudyMate from there to turn this on."}
              {state === "unsupported" && "This browser cannot receive notifications. Email reminders still work."}
              {state === "denied" && "Blocked in your browser settings for this site."}
              {(state === "on" || state === "off") && "Pops up like a message, even when StudyMate is closed."}
              {config && !config.push_available && " (Not set up on the server yet.)"}
            </p>
          </div>
        </div>
        <Toggle
          label="Notifications on this device"
          checked={pushOn}
          onChange={(on) => void togglePush(on)}
        />
      </div>

      <div className="flex items-start justify-between gap-4 p-4">
        <div className="flex gap-3">
          <Mail className="mt-0.5 h-5 w-5 shrink-0 text-ink/50" aria-hidden />
          <div>
            <p className="text-sm font-semibold text-ink">Email reminders</p>
            <p className="text-xs text-ink/60">
              To {user?.email}
              {config && !config.email_available && " (Not set up on the server yet.)"}
            </p>
          </div>
        </div>
        <Toggle label="Email reminders" checked={!!user?.notify_email} onChange={(on) => void toggleEmail(on)} />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 p-4">
        <p className="flex items-center gap-1.5 text-xs text-ink/55">
          {pushOn || user?.notify_email ? (
            <BellRing className="h-3.5 w-3.5" aria-hidden />
          ) : (
            <BellOff className="h-3.5 w-3.5" aria-hidden />
          )}
          An hour before each lecture, when it starts, and when it ends.
        </p>
        <button type="button" onClick={test} disabled={isBusy} className="btn-secondary py-1.5 text-xs">
          <Send className="h-3.5 w-3.5" aria-hidden /> Send a test
        </button>
      </div>

      {message && (
        <div className="p-4">
          <Alert kind={message.kind}>{message.text}</Alert>
        </div>
      )}
    </div>
  );
}
