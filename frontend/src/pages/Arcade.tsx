import {
  CircleX,
  Clock3,
  Flame,
  Gamepad2,
  Gauge,
  Heart,
  Layers3,
  Library,
  Link2,
  ListChecks,
  Lock,
  LucideIcon,
  MousePointerClick,
  Play,
  Shapes,
  Shield,
  Shuffle,
  Swords,
  Timer,
  Trophy,
  Zap,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { DocumentSummary, listDocuments } from "../api/documents";
import { CourseGameStats, GAME_PATHS, GameName, getGameStats } from "../api/games";
import { listChallenges } from "../api/social";
import CourseSelect from "../components/CourseSelect";
import PageHeader from "../components/PageHeader";
import { Spinner } from "../components/ui";

interface GameInfo {
  game: GameName;
  path: string;
  title: string;
  tagline: string;
  /** What the course needs before the game can be played. */
  needs: (stats: CourseGameStats) => { ready: boolean; reason: string; fix: "questions" | "material" };
  /** Each rule with an icon that shows what it is about. */
  rules: [LucideIcon, string][];
  icon: LucideIcon;
  accent: string;
}

const GAMES: GameInfo[] = [
  {
    game: "beat_the_clock",
    path: "clock",
    title: "Beat the Clock",
    tagline: "Ten questions. Fifteen seconds each. How fast are you?",
    rules: [
      [Zap, "Faster answers score more"],
      [Flame, "Streaks multiply your points"],
      [ListChecks, "Uses your multiple-choice and fill-in-the-blank sets"],
    ],
    icon: Timer,
    accent: "from-navy to-navy-light",
    needs: (s) =>
      s.clock_questions_available >= 4
        ? { ready: true, reason: `${s.clock_questions_available} questions in the pool`, fix: "questions" }
        : { ready: false, reason: "Generate a Multiple choice or Fill in the blank set in the Study Engine first.", fix: "questions" },
  },
  {
    game: "concept_match",
    path: "match",
    title: "Concept Match",
    tagline: "Concepts on one side, meanings on the other. Pair them all up.",
    rules: [
      [MousePointerClick, "Tap a concept, then its meaning: green if right, red if not"],
      [CircleX, "Up to eight pairs a round; wrong pairs cost points"],
      [Shuffle, "Each round brings concepts you have not matched yet"],
    ],
    icon: Link2,
    accent: "from-gold-dark to-gold",
    needs: (s) =>
      s.concepts_available >= 3
        ? {
            ready: true,
            reason:
              s.match_fresh_rounds > 0
                ? `${s.concepts_available} concepts · about ${s.match_fresh_rounds} round${s.match_fresh_rounds === 1 ? "" : "s"} of new pairs left`
                : `${s.concepts_available} concepts · all matched at least once, so pairs now repeat. Upload more material for new ones.`,
            fix: "material",
          }
        : { ready: false, reason: "Upload material for this course first; it needs at least three concepts.", fix: "material" },
  },
  {
    game: "true_false",
    path: "blitz",
    title: "True or False Blitz",
    tagline: "Sixty seconds. Is each statement right or wrong?",
    rules: [
      [Clock3, "One minute: judge as many as you can"],
      [Flame, "Streaks multiply your points, up to three times"],
      [Layers3, "Built from your concepts and question sets"],
    ],
    icon: Gauge,
    accent: "from-emerald-700 to-emerald-500",
    needs: (s) =>
      s.concepts_available + s.clock_questions_available >= 6
        ? { ready: true, reason: "Statements from your concepts and questions", fix: "material" }
        : { ready: false, reason: "Upload material or generate a question set first.", fix: "material" },
  },
  {
    game: "odd_one_out",
    path: "odd",
    title: "Odd One Out",
    tagline: "Three concepts belong together. Which one does not?",
    rules: [
      [Shapes, "Six puzzles of four concepts each"],
      [Zap, "Quick answers earn a bonus"],
      [Library, "See how every idea connects after each answer"],
    ],
    icon: Shapes,
    accent: "from-violet-700 to-violet-500",
    needs: (s) =>
      s.concepts_available >= 6
        ? { ready: true, reason: `Puzzles from ${s.concepts_available} concepts`, fix: "material" }
        : { ready: false, reason: "Needs at least six concepts. Upload more material for this course.", fix: "material" },
  },
  {
    game: "three_strikes",
    path: "strikes",
    title: "Three Strikes",
    tagline: "Keep answering until your third mistake.",
    rules: [
      [Heart, "Three lives; every mistake costs one"],
      [Timer, "Less time per question as you go"],
      [Flame, "Points rise every five right answers"],
    ],
    icon: Shield,
    accent: "from-rose-700 to-rose-500",
    needs: (s) =>
      s.clock_questions_available >= 6
        ? { ready: true, reason: `${s.clock_questions_available} questions in the pool`, fix: "questions" }
        : {
            ready: false,
            reason: "Needs six multiple-choice or fill-in-the-blank questions. Generate a set first.",
            fix: "questions",
          },
  },
];

export default function Arcade() {
  const [params, setParams] = useSearchParams();
  const [courseId, setCourseId] = useState<string | null>(params.get("course"));
  const [stats, setStats] = useState<CourseGameStats | null>(null);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  // Concept Match can be played on the whole course or on one file.
  const [matchDocument, setMatchDocument] = useState<string>("");
  const [waiting, setWaiting] = useState(0);

  useEffect(() => {
    listChallenges()
      .then((all) => setWaiting(all.filter((c) => c.direction === "received" && c.status === "open").length))
      .catch(() => setWaiting(0));
  }, []);

  useEffect(() => {
    if (!courseId) return;
    setStats(null);
    setParams({ course: courseId }, { replace: true });
    setMatchDocument("");
    getGameStats(courseId).then(setStats).catch(() => setStats(null));
    listDocuments(courseId)
      .then((found) => setDocuments(found.filter((d) => d.status === "completed")))
      .catch(() => setDocuments([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [courseId]);

  return (
    <>
      <PageHeader
        icon={Gamepad2}
        title="Arcade"
        subtitle="Revise by playing. Every game uses your own course material and earns XP."
      />

      {waiting > 0 && (
        <Link
          to="/friends?tab=challenges"
          className="mb-4 flex items-center gap-3 rounded-xl border border-gold bg-gold/10 px-4 py-3 text-sm font-semibold text-ink hover:bg-gold/20"
        >
          <Swords className="h-5 w-5 shrink-0 text-gold-dark" aria-hidden />
          {waiting === 1 ? "A friend has challenged you." : `${waiting} friends have challenged you.`} Play now
        </Link>
      )}

      <div className="mb-5">
        <CourseSelect selectedCourseId={courseId} onSelect={setCourseId} allowCreate={false} />
      </div>

      {courseId && !stats && <Spinner />}

      {stats && (
        <div className="grid gap-4 md:grid-cols-2">
          {GAMES.map((info) => {
            const { ready, reason, fix } = info.needs(stats);
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
                  <ul className="space-y-1 text-sm text-ink/70">
                    {info.rules.map(([RuleIcon, rule]) => (
                      <li key={rule} className="flex items-start gap-2">
                        <RuleIcon className="mt-0.5 h-3.5 w-3.5 shrink-0 text-gold-dark" aria-hidden />
                        {rule}
                      </li>
                    ))}
                  </ul>
                  <div className="mt-4 flex items-center gap-4 text-xs text-ink/55">
                    <span className="flex items-center gap-1">
                      <Trophy className="h-3.5 w-3.5 text-gold-dark" aria-hidden />
                      Best: <span className="font-semibold text-ink">{record?.best?.toLocaleString() ?? "—"}</span>
                    </span>
                    <span>
                      Played <span className="font-semibold text-ink">{record?.plays ?? 0}</span>×
                    </span>
                  </div>
                  <p className={`mt-3 text-xs ${ready ? "text-ink/45" : "text-red-600"}`}>{reason}</p>
                  {info.game === "concept_match" && ready && documents.length > 1 && (
                    <label className="mt-3 flex items-center gap-2 text-xs text-ink/60">
                      <Library className="h-3.5 w-3.5 shrink-0" aria-hidden />
                      <span className="shrink-0">Match from</span>
                      <select
                        value={matchDocument}
                        onChange={(e) => setMatchDocument(e.target.value)}
                        className="input min-w-0 py-1.5 text-xs"
                      >
                        <option value="">The whole course</option>
                        {documents.map((document) => (
                          <option key={document.id} value={document.id}>
                            {document.filename}
                          </option>
                        ))}
                      </select>
                    </label>
                  )}
                  <div className="mt-auto pt-4">
                    {ready ? (
                      <Link
                        to={`/play/${courseId}/${GAME_PATHS[info.game]}${info.game === "concept_match" && matchDocument ? `?document=${matchDocument}` : ""}`}
                        className="btn-primary w-full py-2.5"
                      >
                        <Play className="h-4 w-4" aria-hidden /> Play
                      </Link>
                    ) : (
                      <Link
                        to={fix === "questions" ? `/study/${courseId}` : `/courses/${courseId}`}
                        className="btn-secondary w-full py-2.5"
                      >
                        <Lock className="h-4 w-4" aria-hidden />
                        {fix === "questions" ? "Generate questions" : "Add material"}
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
