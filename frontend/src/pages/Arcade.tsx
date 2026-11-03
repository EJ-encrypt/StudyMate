import { Gamepad2, Grid3x3, Lock, Play, Sparkles, Timer, Trophy } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { CourseGameStats, GameName, getGameStats } from "../api/games";
import CourseSelect from "../components/CourseSelect";
import PageHeader from "../components/PageHeader";
import { Spinner } from "../components/ui";

interface GameInfo {
  game: GameName;
  path: string;
  title: string;
  tagline: string;
  rules: string[];
  icon: typeof Timer;
  accent: string;
}

const GAMES: GameInfo[] = [
  {
    game: "beat_the_clock",
    path: "clock",
    title: "Beat the Clock",
    tagline: "Ten questions. Fifteen seconds each. How fast are you?",
    rules: ["Faster answers score more", "Streaks multiply your points", "Uses your multiple-choice and fill-in-the-blank sets"],
    icon: Timer,
    accent: "from-navy to-navy-light",
  },
  {
    game: "concept_match",
    path: "match",
    title: "Concept Match",
    tagline: "Flip the cards and pair each concept with its meaning.",
    rules: ["Match all pairs as fast as you can", "Wrong pairs cost points", "Built from your course knowledge base"],
    icon: Grid3x3,
    accent: "from-gold-dark to-gold",
  },
];

export default function Arcade() {
  const [params, setParams] = useSearchParams();
  const [courseId, setCourseId] = useState<string | null>(params.get("course"));
  const [stats, setStats] = useState<CourseGameStats | null>(null);

  useEffect(() => {
    if (!courseId) return;
    setStats(null);
    setParams({ course: courseId }, { replace: true });
    getGameStats(courseId).then(setStats).catch(() => setStats(null));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [courseId]);

  function availability(game: GameName): { ready: boolean; reason: string } {
    if (!stats) return { ready: false, reason: "" };
    if (game === "beat_the_clock") {
      return stats.clock_questions_available >= 4
        ? { ready: true, reason: `${stats.clock_questions_available} questions in the pool` }
        : {
            ready: false,
            reason: "Generate a Multiple choice or Fill in the blank set in the Study Engine first.",
          };
    }
    return stats.concepts_available >= 3
      ? { ready: true, reason: `${stats.concepts_available} concepts to match` }
      : { ready: false, reason: "Upload material for this course first; it needs at least three concepts." };
  }

  return (
    <>
      <PageHeader
        icon={Gamepad2}
        title="Arcade"
        subtitle="Revise by playing. Every game uses your own course material and earns XP."
      />

      <div className="mb-5">
        <CourseSelect selectedCourseId={courseId} onSelect={setCourseId} allowCreate={false} />
      </div>

      {courseId && !stats && <Spinner />}

      {stats && (
        <div className="grid gap-4 md:grid-cols-2">
          {GAMES.map((info) => {
            const { ready, reason } = availability(info.game);
            const record = stats.games.find((g) => g.game === info.game);
            const Icon = info.icon;
            return (
              <article key={info.game} className="card flex flex-col overflow-hidden">
                <div className={`relative bg-gradient-to-br ${info.accent} p-5 text-white`}>
                  <Icon className="absolute -right-3 -top-3 h-24 w-24 opacity-10" aria-hidden />
                  <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-white/15">
                    <Icon className="h-6 w-6" aria-hidden />
                  </span>
                  <h2 className="mt-3 text-lg font-bold">{info.title}</h2>
                  <p className="text-sm text-white/80">{info.tagline}</p>
                </div>
                <div className="flex flex-1 flex-col p-4">
                  <ul className="space-y-1 text-sm text-navy/70">
                    {info.rules.map((rule) => (
                      <li key={rule} className="flex items-start gap-2">
                        <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-gold-dark" aria-hidden />
                        {rule}
                      </li>
                    ))}
                  </ul>
                  <div className="mt-4 flex items-center gap-4 text-xs text-navy/55">
                    <span className="flex items-center gap-1">
                      <Trophy className="h-3.5 w-3.5 text-gold-dark" aria-hidden />
                      Best: <span className="font-semibold text-navy">{record?.best?.toLocaleString() ?? "—"}</span>
                    </span>
                    <span>
                      Played <span className="font-semibold text-navy">{record?.plays ?? 0}</span>×
                    </span>
                  </div>
                  <p className={`mt-3 text-xs ${ready ? "text-navy/45" : "text-red-600"}`}>{reason}</p>
                  <div className="mt-auto pt-4">
                    {ready ? (
                      <Link to={`/play/${courseId}/${info.path}`} className="btn-primary w-full py-2.5">
                        <Play className="h-4 w-4" aria-hidden /> Play
                      </Link>
                    ) : (
                      <Link
                        to={info.game === "beat_the_clock" ? `/study/${courseId}` : `/courses/${courseId}`}
                        className="btn-secondary w-full py-2.5"
                      >
                        <Lock className="h-4 w-4" aria-hidden />
                        {info.game === "beat_the_clock" ? "Generate questions" : "Add material"}
                      </Link>
                    )}
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </>
  );
}
