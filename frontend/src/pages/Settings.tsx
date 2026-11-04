import {
  Ban,
  BellRing,
  Compass,
  KeyRound,
  Monitor,
  Moon,
  Save,
  Settings as SettingsIcon,
  Sun,
  Target,
  Trash2,
  Trophy,
  UserRound,
} from "lucide-react";
import { FormEvent, ReactNode, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { updatePreferences } from "../api/auth";
import { errorMessage } from "../api/client";
import { BlockedStudent, getProgrammes, listBlocked, unblockStudent } from "../api/social";
import NotificationSettings from "../components/NotificationSettings";
import PageHeader from "../components/PageHeader";
import { Alert, PasswordInput } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { Captcha, captchaEnabled } from "../lib/captcha";
import { getThemeChoice, setThemeChoice, ThemeChoice } from "../lib/theme";
import { toast } from "../lib/toast";

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
  const [programme, setProgramme] = useState(user?.programme ?? "");
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [level, setLevel] = useState(user?.level ?? 100);
  const [semester, setSemester] = useState(user?.semester ?? 1);
  const [message, setMessage] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    setFullName(user?.full_name ?? "");
    setUsername(user?.username ?? "");
    setProgramme(user?.programme ?? "");
    setLevel(user?.level ?? 100);
    setSemester(user?.semester ?? 1);
  }, [user]);

  async function save(event: FormEvent) {
    event.preventDefault();
    setIsSaving(true);
    setMessage(null);
    try {
      await updatePreferences({
        full_name: fullName.trim(),
        username: username.trim(),
        level,
        semester,
        ...(programme.trim() ? { programme: programme.trim() } : {}),
      });
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
      <label className="sm:col-span-2">
        <span className="label">Programme</span>
        <input
          value={programme}
          onChange={(e) => setProgramme(e.target.value)}
          onFocus={() => {
            if (suggestions.length === 0) getProgrammes().then(setSuggestions).catch(() => undefined);
          }}
          list="programme-suggestions"
          placeholder="BSc Information Technology"
          className="input mt-1"
        />
        <datalist id="programme-suggestions">
          {suggestions.map((name) => (
            <option key={name} value={name} />
          ))}
        </datalist>
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
  const { changePassword, addPassword, hasPassword } = useAuth();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [message, setMessage] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [captchaToken, setCaptchaToken] = useState<string | null>(null);
  const [captchaRound, setCaptchaRound] = useState(0);
  // Checking the current password is a sign-in, which CAPTCHA protection covers.
  const needsCaptcha = hasPassword && captchaEnabled;

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
      if (hasPassword) {
        await changePassword(current, next, captchaToken ?? undefined);
        setMessage({ kind: "success", text: "Password changed." });
      } else {
        await addPassword(next);
        setMessage({ kind: "success", text: "Password added. You can now log in with your email too." });
      }
      setCurrent("");
      setNext("");
      setConfirm("");
    } catch (err) {
      setMessage({ kind: "error", text: err instanceof Error ? err.message : "Could not change your password." });
    } finally {
      setIsSaving(false);
      if (needsCaptcha) setCaptchaRound((round) => round + 1);
    }
  }

  return (
    <form onSubmit={save} className={`card grid gap-3 p-4 ${hasPassword ? "sm:grid-cols-3" : "sm:grid-cols-2"}`}>
      {!hasPassword && (
        <p className="text-sm text-ink/65 sm:col-span-2">
          You signed up with Google, so this account has no password yet. Add one to also log in with your
          email address.
        </p>
      )}
      {hasPassword && (
        <label>
          <span className="label">Current password</span>
          <PasswordInput
            required
            autoComplete="current-password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            className="mt-1"
          />
        </label>
      )}
      <label>
        <span className="label">New password</span>
        <PasswordInput
          required
          autoComplete="new-password"
          value={next}
          onChange={(e) => setNext(e.target.value)}
          className="mt-1"
        />
      </label>
      <label>
        <span className="label">Confirm new password</span>
        <PasswordInput
          required
          autoComplete="new-password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          className="mt-1"
        />
      </label>
      {needsCaptcha && (
        <div className="sm:col-span-3">
          <Captcha key={captchaRound} onToken={setCaptchaToken} />
        </div>
      )}
      {message && (
        <div className="sm:col-span-3">
          <Alert kind={message.kind}>{message.text}</Alert>
        </div>
      )}
      <div className="sm:col-span-3">
        <button type="submit" disabled={isSaving || (needsCaptcha && !captchaToken)} className="btn-primary">
          <KeyRound className="h-4 w-4" aria-hidden />{" "}
          {hasPassword ? (isSaving ? "Changing..." : "Change password") : isSaving ? "Adding..." : "Add password"}
        </button>
      </div>
    </form>
  );
}

const GOALS = [1, 2, 3, 4, 5, 6, 8, 10];

function DailyGoal() {
  const { user, refresh } = useAuth();
  const [isSaving, setIsSaving] = useState(false);
  const goal = user?.daily_goal ?? 3;

  async function choose(value: number) {
    if (value === goal) return;
    setIsSaving(true);
    try {
      await updatePreferences({ daily_goal: value });
      await refresh();
      toast(`Daily goal set to ${value} session${value === 1 ? "" : "s"}.`);
    } catch (err) {
      toast(errorMessage(err, "Could not save your goal."), { kind: "error" });
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="card p-4">
      <p className="text-sm text-ink/70">
        Study sessions a day: each Arcade round or quiz counts as one, and every ten flashcards as one more. Your
        progress shows on Profile.
      </p>
      <div className="mt-3 flex flex-wrap gap-2" role="radiogroup" aria-label="Daily goal">
        {GOALS.map((value) => (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={goal === value}
            disabled={isSaving}
            onClick={() => void choose(value)}
            className={[
              "h-10 w-10 rounded-full text-sm font-bold transition",
              goal === value ? "bg-navy text-gold" : "bg-ink/5 text-ink/70 hover:bg-ink/10",
            ].join(" ")}
          >
            {value}
          </button>
        ))}
      </div>
    </div>
  );
}

function BlockedStudents() {
  const [blocked, setBlocked] = useState<BlockedStudent[] | null>(null);

  useEffect(() => {
    listBlocked()
      .then(setBlocked)
      .catch(() => setBlocked([]));
  }, []);

  async function unblock(student: BlockedStudent) {
    try {
      await unblockStudent(student.id);
      setBlocked((current) => current?.filter((s) => s.id !== student.id) ?? null);
      toast(`${student.name} is unblocked.`);
    } catch (err) {
      toast(errorMessage(err, "Could not unblock them."), { kind: "error" });
    }
  }

  if (blocked === null) return null;
  return (
    <div className="card p-4">
      {blocked.length === 0 ? (
        <p className="text-sm text-ink/60">
          Nobody. Block someone from the ... menu beside them on the Leaderboard; they are not told.
        </p>
      ) : (
        <ul className="divide-y divide-ink/5">
          {blocked.map((student) => (
            <li key={student.id} className="flex items-center justify-between gap-3 py-2">
              <span className="truncate text-sm text-ink">{student.name}</span>
              <button type="button" onClick={() => void unblock(student)} className="btn-ghost text-xs">
                Unblock
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function LeaderboardSetting() {
  const { user, refresh } = useAuth();
  const [isSaving, setIsSaving] = useState(false);
  const joined = !!user?.public_leaderboard;

  async function toggle() {
    setIsSaving(true);
    try {
      await updatePreferences({ public_leaderboard: !joined });
      await refresh();
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="card flex items-start justify-between gap-4 p-4">
      <div>
        <p className="text-sm font-semibold text-ink">Show me on my programme's leaderboard</p>
        <p className="mt-0.5 text-xs text-ink/55">
          Everyone on {user?.programme ?? "your programme"} who joins can see your{" "}
          {user?.username ? `username (@${user.username})` : "first name and initial"} and XP. Nothing else. Friends always
          see each other.
        </p>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={joined}
        aria-label="Show me on my programme's leaderboard"
        disabled={isSaving}
        onClick={() => void toggle()}
        className={[
          "relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition",
          joined ? "bg-navy" : "bg-ink/20",
        ].join(" ")}
      >
        <span
          className={[
            "inline-block h-5 w-5 transform rounded-full bg-white shadow transition",
            joined ? "translate-x-5" : "translate-x-0.5",
          ].join(" ")}
        />
      </button>
    </div>
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
      <Section icon={Target} title="Daily goal">
        <DailyGoal />
      </Section>
      <Section icon={Trophy} title="Leaderboards">
        <LeaderboardSetting />
      </Section>
      <Section icon={Ban} title="Blocked students">
        <BlockedStudents />
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
