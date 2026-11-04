import {
  Award,
  BookOpenCheck,
  Flame,
  Gamepad2,
  Lock,
  LogOut,
  LucideIcon,
  Medal,
  NotebookPen,
  Rocket,
  Settings,
  Shield,
  Star,
  Swords,
  Target,
  Timer,
  Trophy,
  UploadCloud,
  UserCircle,
  Users,
  Zap,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getProgress, ProgressSummary } from "../api/profile";
import PageHeader from "../components/PageHeader";
import { Alert, Spinner, StatTile } from "../components/ui";
import { useAuth } from "../context/AuthContext";

const BADGE_ICONS: Record<string, LucideIcon> = {
  first_upload: UploadCloud,
  first_quiz: BookOpenCheck,
  perfect_score: Star,
  streak_3: Flame,
  streak_7: Rocket,
  concept_mastered: Target,
  ten_concepts: Medal,
  exam_ready: Trophy,
  first_game: Gamepad2,
  speed_demon: Timer,
  perfect_memory: Zap,
  reflective: NotebookPen,
  survivor: Shield,
  first_friend: Users,
  challenge_won: Swords,
};

export default function Profile() {
  const { user, logout } = useAuth();
  const [progress, setProgress] = useState<ProgressSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getProgress()
      .then(setProgress)
      .catch(() => setError("Could not load your progress."));
  }, []);

  const earned = progress?.badges.filter((badge) => badge.earned_at !== null) ?? [];

  return (
    <>
      <PageHeader
        icon={UserCircle}
        title={user?.full_name ?? "Profile"}
        subtitle={[user?.programme, user?.level ? `Level ${user.level}` : null].filter(Boolean).join(" · ") || user?.email}
        actions={
          <>
            <Link to="/friends" className="btn-gold">
              <Users className="h-4 w-4" aria-hidden /> Leaderboard & friends
            </Link>
            <button type="button" onClick={() => void logout()} className="btn-secondary md:hidden">
              <LogOut className="h-4 w-4" aria-hidden /> Log out
            </button>
          </>
        }
      />

      {error && <Alert>{error}</Alert>}
      {!progress && !error && <Spinner />}

      {progress && (
        <>
          <section className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatTile icon={Zap} tone="amber" label="XP" value={progress.xp.toLocaleString()} />
            <StatTile icon={Flame} tone="fire" label="Day streak" value={progress.current_streak} />
            <StatTile icon={Trophy} tone="violet" label="Best streak" value={progress.longest_streak} />
            <StatTile icon={BookOpenCheck} tone="sky" label="Quizzes taken" value={progress.attempts} />
          </section>

          <p className="mt-3 text-sm text-ink/60">
            {progress.documents} document{progress.documents === 1 ? "" : "s"} uploaded
            {progress.last_active_on && ` · last studied ${progress.last_active_on}`}
          </p>

          <section className="mt-6">
            <h2 className="section-title">
              <Award className="h-3.5 w-3.5" aria-hidden /> Badges · {earned.length} of {progress.badges.length}
            </h2>
            <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
              {progress.badges.map((badge) => {
                const Icon = BADGE_ICONS[badge.code] ?? Award;
                const unlocked = badge.earned_at !== null;
                return (
                  <li
                    key={badge.code}
                    className={[
                      "flex flex-col items-center rounded-xl border p-3 text-center",
                      unlocked ? "border-gold bg-gradient-to-b from-gold/15 to-surface shadow-card" : "border-ink/10 bg-surface/60",
                    ].join(" ")}
                  >
                    <span
                      className={[
                        "flex h-11 w-11 items-center justify-center rounded-full",
                        unlocked ? "bg-navy text-gold" : "bg-ink/5 text-ink/30",
                      ].join(" ")}
                    >
                      {unlocked ? <Icon className="h-5 w-5" aria-hidden /> : <Lock className="h-4 w-4" aria-hidden />}
                    </span>
                    <p className={`mt-2 text-sm font-semibold ${unlocked ? "text-ink" : "text-ink/50"}`}>{badge.name}</p>
                    <p className="mt-0.5 text-xs text-ink/55">{badge.description}</p>
                  </li>
                );
              })}
            </ul>
          </section>
        </>
      )}

      <section className="mt-8">
        <h2 className="section-title">Account</h2>
        <dl className="card grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 p-4 text-sm">
          {user?.username && (
            <>
              <dt className="text-ink/55">Username</dt>
              <dd className="truncate text-ink">@{user.username}</dd>
            </>
          )}
          <dt className="text-ink/55">Email</dt>
          <dd className="truncate text-ink">{user?.email}</dd>
          <dt className="text-ink/55">School</dt>
          <dd className="text-ink">{user?.school ?? "—"}</dd>
          <dt className="text-ink/55">Time zone</dt>
          <dd className="text-ink">{user?.timezone}</dd>
        </dl>
        <Link to="/settings" className="btn-secondary mt-3">
          <Settings className="h-4 w-4" aria-hidden /> Settings and reminders
        </Link>
      </section>
    </>
  );
}
