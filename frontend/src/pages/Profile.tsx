import {
  Award,
  BookOpenCheck,
  Flame,
  Gamepad2,
  Lock,
  LucideIcon,
  Medal,
  NotebookPen,
  Rocket,
  Shield,
  Star,
  Swords,
  Target,
  Timer,
  Trophy,
  UploadCloud,
  Users,
  Zap,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";

import { getProgress, ProgressSummary } from "../api/profile";
import DailyGoalRing from "../components/DailyGoalRing";
import { Alert, ListSkeleton, StatTile } from "../components/ui";

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

/** XP, streaks, today's goal and badges: shown in Settings, under Progress & badges. */
export function ProgressPanel() {
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
      {error && <Alert>{error}</Alert>}
      {!progress && !error && <ListSkeleton rows={2} />}

      {progress && (
        <>
          <DailyGoalRing done={progress.done_today} goal={progress.daily_goal} />
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

    </>
  );
}

/** The old Profile address, kept so earlier links and notifications still land somewhere. */
export default function Profile() {
  return <Navigate to="/settings?section=progress" replace />;
}
