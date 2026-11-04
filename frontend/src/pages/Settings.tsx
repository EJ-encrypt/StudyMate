import {
  BellRing,
  Compass,
  KeyRound,
  Monitor,
  Moon,
  Save,
  Settings as SettingsIcon,
  Sun,
  Trash2,
  UserRound,
} from "lucide-react";
import { FormEvent, ReactNode, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { updatePreferences } from "../api/auth";
import { errorMessage } from "../api/client";
import NotificationSettings from "../components/NotificationSettings";
import PageHeader from "../components/PageHeader";
import { Alert } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { getThemeChoice, setThemeChoice, ThemeChoice } from "../lib/theme";

const LEVELS = [100, 200, 300, 400, 500, 600];
const MIN_PASSWORD = 8;

function Section({ icon: Icon, title, children }: { icon: typeof Sun; title: string; children: ReactNode }) {
  return (
    <section className="mb-6">
      <h2 className="section-title">
        <Icon className="h-3.5 w-3.5" aria-hidden /> {title}
      </h2>
      {children}
    </section>
  );
}

function Appearance() {
  const [choice, setChoice] = useState<ThemeChoice>(getThemeChoice);
  const options: { value: ThemeChoice; label: string; icon: typeof Sun }[] = [
    { value: "light", label: "Light", icon: Sun },
    { value: "dark", label: "Dark", icon: Moon },
    { value: "system", label: "System", icon: Monitor },
  ];

  return (
    <div className="card p-4">
      <div role="radiogroup" aria-label="Theme" className="grid grid-cols-3 gap-2">
        {options.map(({ value, label, icon: Icon }) => (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={choice === value}
            onClick={() => {
              setChoice(value);
              setThemeChoice(value);
            }}
            className={[
              "flex flex-col items-center gap-1.5 rounded-lg border-2 px-2 py-3 text-sm font-semibold transition",
              choice === value ? "border-gold bg-gold/10 text-ink" : "border-ink/10 text-ink/70 hover:border-ink/25",
            ].join(" ")}
          >
            <Icon className="h-5 w-5" aria-hidden />
            {label}
          </button>
        ))}
      </div>
      <p className="mt-3 text-xs text-ink/55">
        System follows your phone or computer, switching to dark when it does. Saved on this device.
      </p>
    </div>
  );
}

function ProfileForm() {
  const { user, refresh } = useAuth();
  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const [username, setUsername] = useState(user?.username ?? "");
  const [level, setLevel] = useState(user?.level ?? 100);
  const [semester, setSemester] = useState(user?.semester ?? 1);
  const [message, setMessage] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    setFullName(user?.full_name ?? "");
    setUsername(user?.username ?? "");
    setLevel(user?.level ?? 100);
    setSemester(user?.semester ?? 1);
  }, [user]);

  async function save(event: FormEvent) {
    event.preventDefault();
    setIsSaving(true);
    setMessage(null);
    try {
      await updatePreferences({ full_name: fullName.trim(), username: username.trim(), level, semester });
      await refresh();
      setMessage({ kind: "success", text: "Saved." });
    } catch (err) {
      setMessage({ kind: "error", text: errorMessage(err, "Could not save your details.") });
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <form onSubmit={save} className="card grid gap-3 p-4 sm:grid-cols-2">
      <label>
        <span className="label">Name</span>
        <input required value={fullName} onChange={(e) => setFullName(e.target.value)} className="input mt-1" />
      </label>
      <label>
        <span className="label">Username</span>
        <div className="relative mt-1">
          <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-sm text-ink/40">@</span>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value.replace(/^@/, ""))}
            placeholder="kofi_m"
            pattern="[A-Za-z0-9_.]{3,30}"
            title="3 to 30 letters, numbers, dots or underscores"
            autoCapitalize="none"
            autoCorrect="off"
            className="input pl-7"
          />
        </div>
      </label>
      <label>
        <span className="label">Current level</span>
        <select value={level} onChange={(e) => setLevel(Number(e.target.value))} className="input mt-1">
          {LEVELS.map((value) => (
            <option key={value} value={value}>
              Level {value}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span className="label">Current semester</span>
        <select value={semester} onChange={(e) => setSemester(Number(e.target.value))} className="input mt-1">
          <option value={1}>Semester 1</option>
          <option value={2}>Semester 2</option>
        </select>
      </label>
      <p className="text-xs text-ink/55 sm:col-span-2">
        New courses are filed under your current level and semester. Change these when you move on, and earlier
        courses stay where they were.
      </p>
      {message && (
        <div className="sm:col-span-2">
          <Alert kind={message.kind}>{message.text}</Alert>
        </div>
      )}
      <div className="sm:col-span-2">
        <button type="submit" disabled={isSaving} className="btn-primary">
          <Save className="h-4 w-4" aria-hidden /> {isSaving ? "Saving..." : "Save"}
        </button>
      </div>
    </form>
  );
}

function PasswordForm() {
  const { changePassword } = useAuth();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [message, setMessage] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  async function save(event: FormEvent) {
    event.preventDefault();
    setMessage(null);
    if (next.length < MIN_PASSWORD) {
      setMessage({ kind: "error", text: `Use at least ${MIN_PASSWORD} characters.` });
      return;
    }
    if (next !== confirm) {
      setMessage({ kind: "error", text: "The new passwords do not match." });
      return;
    }
    setIsSaving(true);
    try {
      await changePassword(current, next);
      setCurrent("");
      setNext("");
      setConfirm("");
      setMessage({ kind: "success", text: "Password changed." });
    } catch (err) {
      setMessage({ kind: "error", text: err instanceof Error ? err.message : "Could not change your password." });
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <form onSubmit={save} className="card grid gap-3 p-4 sm:grid-cols-3">
      <label>
        <span className="label">Current password</span>
        <input
          type="password"
          required
          autoComplete="current-password"
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
          className="input mt-1"
        />
      </label>
      <label>
        <span className="label">New password</span>
        <input
          type="password"
          required
          autoComplete="new-password"
          value={next}
          onChange={(e) => setNext(e.target.value)}
          className="input mt-1"
        />
      </label>
      <label>
        <span className="label">Confirm new password</span>
        <input
          type="password"
          required
          autoComplete="new-password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          className="input mt-1"
        />
      </label>
      {message && (
        <div className="sm:col-span-3">
          <Alert kind={message.kind}>{message.text}</Alert>
        </div>
      )}
      <div className="sm:col-span-3">
        <button type="submit" disabled={isSaving} className="btn-primary">
          <KeyRound className="h-4 w-4" aria-hidden /> {isSaving ? "Changing..." : "Change password"}
        </button>
      </div>
    </form>
  );
}

function Tutorial() {
  const { refresh } = useAuth();
  const navigate = useNavigate();
  const [isBusy, setIsBusy] = useState(false);

  async function replay() {
    setIsBusy(true);
    try {
      await updatePreferences({ tutorial_seen: false });
      await refresh();
      navigate("/courses");
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <div className="card flex flex-wrap items-center justify-between gap-3 p-4">
      <p className="text-sm text-ink/70">A quick walk through how StudyMate works, step by step.</p>
      <button type="button" onClick={() => void replay()} disabled={isBusy} className="btn-secondary">
        <Compass className="h-4 w-4" aria-hidden /> Show the tutorial again
      </button>
    </div>
  );
}

function DeleteAccount() {
  const { deleteAccount } = useAuth();
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const [typed, setTyped] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  async function confirmDelete(event: FormEvent) {
    event.preventDefault();
    setIsDeleting(true);
    setError(null);
    try {
      await deleteAccount();
      navigate("/login", { replace: true });
    } catch (err) {
      setError(errorMessage(err, "Could not delete your account. Please try again."));
      setIsDeleting(false);
    }
  }

  return (
    <div className="card border-red-200 p-4">
      <p className="text-sm text-ink/70">
        Deletes your account and everything in it: courses, uploaded files, quizzes, scores, badges and your
        timetable. This cannot be undone.
      </p>
      {!isOpen ? (
        <button type="button" onClick={() => setIsOpen(true)} className="btn-secondary mt-3 text-red-600">
          <Trash2 className="h-4 w-4" aria-hidden /> Delete my account
        </button>
      ) : (
        <form onSubmit={confirmDelete} className="mt-3 space-y-3">
          <label className="block">
            <span className="label">Type DELETE to confirm</span>
            <input
              value={typed}
              onChange={(e) => setTyped(e.target.value)}
              autoCapitalize="characters"
              autoComplete="off"
              className="input mt-1 sm:max-w-xs"
            />
          </label>
          {error && <Alert>{error}</Alert>}
          <div className="flex flex-wrap gap-2">
            <button type="submit" disabled={typed.trim() !== "DELETE" || isDeleting} className="btn-danger">
              <Trash2 className="h-4 w-4" aria-hidden /> {isDeleting ? "Deleting..." : "Delete everything"}
            </button>
            <button
              type="button"
              onClick={() => {
                setIsOpen(false);
                setTyped("");
              }}
              className="btn-ghost"
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

export default function Settings() {
  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader icon={SettingsIcon} title="Settings" subtitle="Appearance, your details, reminders and account." />
      <Section icon={Sun} title="Appearance">
        <Appearance />
      </Section>
      <Section icon={UserRound} title="Your details">
        <ProfileForm />
      </Section>
      <Section icon={BellRing} title="Lecture reminders">
        <NotificationSettings />
      </Section>
      <Section icon={KeyRound} title="Password">
        <PasswordForm />
      </Section>
      <Section icon={Compass} title="Help">
        <Tutorial />
      </Section>
      <Section icon={Trash2} title="Delete account">
        <DeleteAccount />
      </Section>
    </div>
  );
}
