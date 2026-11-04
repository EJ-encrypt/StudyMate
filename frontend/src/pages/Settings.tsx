import {
  Award,
  BellRing,
  Camera,
  ChevronLeft,
  ChevronRight,
  Compass,
  FileText,
  KeyRound,
  LogOut,
  LucideIcon,
  Monitor,
  Moon,
  Save,
  ShieldCheck,
  Smartphone,
  Sun,
  Target,
  Trash2,
  UserRound,
} from "lucide-react";
import { FormEvent, ReactNode, useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { updatePreferences } from "../api/auth";
import { errorMessage } from "../api/client";
import { BlockedStudent, getProgrammes, listBlocked, unblockStudent } from "../api/social";
import NotificationSettings from "../components/NotificationSettings";
import TermsOfUse from "../components/TermsOfUse";
import { Alert, PasswordInput } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { showInstallHelp } from "../lib/installHelp";
import { enablePush, getNotificationConfig, isIos, pushState, PushState } from "../lib/push";
import { Captcha, captchaEnabled } from "../lib/captcha";
import { getThemeChoice, setThemeChoice, ThemeChoice } from "../lib/theme";
import { toast } from "../lib/toast";
import { startTour } from "../lib/tour";
import { ProgressPanel } from "./Profile";

const LEVELS = [100, 200, 300, 400, 500, 600];
const MIN_PASSWORD = 8;

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

function Permissions() {
  const [state, setState] = useState<PushState | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  useEffect(() => {
    pushState().then(setState).catch(() => setState("unsupported"));
  }, []);

  async function allow() {
    setIsBusy(true);
    try {
      const config = await getNotificationConfig();
      setState(await enablePush(config.vapid_public_key));
    } catch {
      toast("Could not turn on notifications.", { kind: "error" });
    } finally {
      setIsBusy(false);
    }
  }

  const blockedHelp = isIos()
    ? "Your iPhone is blocking this. Open the Settings app, find StudyMate under Notifications, and turn it on."
    : /android/i.test(navigator.userAgent)
      ? "Your phone is blocking this. Open Settings, Apps, then your browser or StudyMate, Notifications, and allow it."
      : "Your browser is blocking this. Click the icon left of the address bar, allow notifications, then reload.";

  const badge: Record<PushState, { label: string; className: string }> = {
    on: { label: "Allowed", className: "bg-green-100 text-green-800" },
    off: { label: "Not turned on", className: "bg-ink/10 text-ink/70" },
    denied: { label: "Blocked", className: "bg-red-100 text-red-700" },
    "needs-install": { label: "Needs Home Screen", className: "bg-gold/25 text-ink" },
    unsupported: { label: "Not supported", className: "bg-ink/10 text-ink/60" },
  };

  return (
    <div className="card divide-y divide-ink/5 p-4">
      <div className="flex items-start gap-3 pb-4">
        <BellRing className="mt-0.5 h-5 w-5 shrink-0 text-ink/55" aria-hidden />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-medium text-ink">Notifications</p>
            {state && (
              <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${badge[state].className}`}>
                {badge[state].label}
              </span>
            )}
          </div>
          <p className="mt-0.5 text-sm text-ink/60">
            {state === "denied"
              ? blockedHelp
              : state === "needs-install"
                ? "On an iPhone, reminders only reach StudyMate once it is on your Home Screen: tap Share in Safari, then Add to Home Screen, and open it from there."
                : "Lecture reminders, friend requests and challenges on this device, even when StudyMate is closed."}
          </p>
          {state === "off" && (
            <button type="button" onClick={() => void allow()} disabled={isBusy} className="btn-secondary mt-2 py-1.5">
              Allow notifications
            </button>
          )}
          {state === "needs-install" && (
            <button type="button" onClick={showInstallHelp} className="btn-secondary mt-2 py-1.5">
              Show me how
            </button>
          )}
        </div>
      </div>
      <div className="flex items-start gap-3 pt-4">
        <Camera className="mt-0.5 h-5 w-5 shrink-0 text-ink/55" aria-hidden />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-medium text-ink">Camera</p>
            <span className="rounded-full bg-ink/10 px-2 py-0.5 text-xs font-semibold text-ink/70">Asked each time</span>
          </div>
          <p className="mt-0.5 text-sm text-ink/60">
            Photographing notes or a timetable opens your phone's own camera. StudyMate only sees the photos you
            choose to save.
          </p>
        </div>
      </div>
    </div>
  );
}

// --- The menu ---------------------------------------------------------------------

interface SubPage {
  title: string;
  description: string;
  body: () => JSX.Element;
}

const PAGES: Record<string, SubPage> = {
  progress: { title: "Progress & badges", description: "Your XP, streaks, today's goal and the badges you have earned.", body: ProgressPanel },
  goal: { title: "Daily goal", description: "How many study sessions make a good day.", body: DailyGoal },
  profile: { title: "Profile", description: "Your name, username, programme, and the level and semester you are in.", body: ProfileForm },
  password: { title: "Password", description: "Change the password you log in with.", body: PasswordForm },
  privacy: {
    title: "Privacy",
    description: "Who sees you on leaderboards, and who you have blocked.",
    body: () => (
      <div className="space-y-5">
        <LeaderboardSetting />
        <div>
          <h3 className="section-title">Blocked students</h3>
          <BlockedStudents />
        </div>
      </div>
    ),
  },
  reminders: { title: "Lecture reminders", description: "How reminders before and after each lecture reach you.", body: NotificationSettings },
  permissions: { title: "Permissions", description: "What StudyMate may use on this device. Nothing is turned on without asking you.", body: Permissions },
  appearance: { title: "Appearance", description: "Light, dark, or whatever your device uses.", body: Appearance },
  terms: { title: "Terms of use", description: "The rules for using StudyMate, and what happens to your information.", body: TermsOfUse },
  delete: { title: "Delete account", description: "Remove your account and everything in it.", body: DeleteAccount },
};

function Group({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section>
      <h2 className="mb-1.5 px-4 text-xs font-semibold uppercase tracking-wider text-ink/50">{title}</h2>
      <div className="card divide-y divide-ink/5 overflow-hidden">{children}</div>
    </section>
  );
}

function Row({
  icon: Icon,
  label,
  value,
  onClick,
  chevron = true,
  danger = false,
  tour,
}: {
  icon: LucideIcon;
  label: string;
  value?: ReactNode;
  onClick: () => void;
  chevron?: boolean;
  danger?: boolean;
  tour?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      data-tour={tour}
      className="flex w-full items-center gap-3 px-4 py-3.5 text-left transition-colors hover:bg-ink/5"
    >
      <Icon className={`h-[18px] w-[18px] shrink-0 ${danger ? "text-red-600" : "text-ink/50"}`} aria-hidden />
      <span className={`flex-1 font-medium ${danger ? "text-red-600" : "text-ink"}`}>{label}</span>
      {value !== undefined && <span className="truncate text-sm text-ink/55">{value}</span>}
      {chevron && <ChevronRight className="h-[18px] w-[18px] shrink-0 text-ink/30" aria-hidden />}
    </button>
  );
}

const THEME_LABELS: Record<ThemeChoice, string> = { light: "Light", dark: "Dark", system: "System" };

export default function Settings() {
  const { user, hasPassword, logout } = useAuth();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const page = PAGES[params.get("section") ?? ""];

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [page]);

  function open(section: string) {
    setParams({ section });
  }

  function back() {
    // Back to the menu the way the student came, so the phone's back gesture agrees.
    if ((window.history.state?.idx ?? 0) > 0) navigate(-1);
    else setParams({}, { replace: true });
  }

  if (page) {
    const Body = page.body;
    return (
      <div className="mx-auto flex max-w-2xl flex-col gap-4">
        <button
          type="button"
          onClick={back}
          className="inline-flex items-center gap-1 self-start rounded-full border border-ink/15 bg-surface py-1.5 pl-2 pr-4 text-sm font-semibold text-ink shadow-sm transition hover:border-gold hover:bg-gold/10"
        >
          <ChevronLeft className="h-4 w-4" aria-hidden /> Settings
        </button>
        <div>
          <h1 className="text-xl font-bold text-ink">{page.title}</h1>
          <p className="text-sm text-ink/60">{page.description}</p>
        </div>
        <Body />
      </div>
    );
  }

  const name = user?.username ? `@${user.username}` : user?.full_name ?? "Student";

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6">
      <h1 className="text-2xl font-bold tracking-tight text-ink">Settings</h1>

      <div className="flex items-center gap-3">
        <span
          className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-navy text-lg font-bold uppercase text-gold"
          aria-hidden
        >
          {(user?.full_name || name).replace("@", "")[0]}
        </span>
        <div className="min-w-0">
          <p className="truncate font-semibold text-ink">{user?.full_name}</p>
          <p className="truncate text-sm text-ink/55">
            {user?.username ? `@${user.username} · ` : ""}
            {user?.email}
          </p>
        </div>
      </div>

      <Group title="Your progress">
        <Row icon={Award} label="Progress & badges" onClick={() => open("progress")} tour="settings-progress" />
        <Row icon={Target} label="Daily goal" value={`${user?.daily_goal ?? 3} a day`} onClick={() => open("goal")} />
      </Group>

      <Group title="Personal information">
        <Row
          icon={UserRound}
          label="Profile"
          value={user?.level ? `Level ${user.level} · Sem ${user.semester ?? 1}` : undefined}
          onClick={() => open("profile")}
        />
        <Row icon={KeyRound} label="Password" value={hasPassword ? undefined : "Not set"} onClick={() => open("password")} />
        <Row
          icon={ShieldCheck}
          label="Privacy"
          value={user?.public_leaderboard ? "On programme board" : undefined}
          onClick={() => open("privacy")}
        />
      </Group>

      <Group title="Preferences">
        <Row icon={BellRing} label="Lecture reminders" onClick={() => open("reminders")} />
        <Row icon={Smartphone} label="Permissions" onClick={() => open("permissions")} />
        <Row icon={Sun} label="Appearance" value={THEME_LABELS[getThemeChoice()]} onClick={() => open("appearance")} />
      </Group>

      <Group title="Support">
        <Row icon={Compass} label="App tour" onClick={startTour} chevron={false} tour="settings-tour" />
        <Row icon={FileText} label="Terms of use" onClick={() => open("terms")} />
      </Group>

      <Group title="Account">
        <Row icon={LogOut} label="Log out" onClick={() => void logout()} chevron={false} />
        <Row icon={Trash2} label="Delete account" onClick={() => open("delete")} danger />
      </Group>
    </div>
  );
}
