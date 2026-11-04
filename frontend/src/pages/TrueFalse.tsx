import { Check, CheckCircle2, Flame, Gauge, X, XCircle } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { BlitzRound, RoundAnswer } from "../api/games";
import GameResultCard from "../components/GameResultCard";
import { GameError, GameIntro } from "../components/GameIntro";
import MathText from "../components/MathText";
import { Alert, Spinner } from "../components/ui";
import { useArcadeRound } from "../lib/useArcadeRound";

const FEEDBACK_MS = 650;

/** True or False Blitz: judge as many statements as you can in a minute. */
export default function TrueFalse() {
  const { round, result, error, load, submit, backTo } = useArcadeRound<BlitzRound>("true-false");
  const [phase, setPhase] = useState<"ready" | "playing" | "submitting" | "done">("ready");
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<(RoundAnswer & { correct: boolean })[]>([]);
  const [streak, setStreak] = useState(0);
  const [feedback, setFeedback] = useState<boolean | null>(null);
  const [remainingMs, setRemainingMs] = useState(0);
  const startedAt = useRef(0);
  const shownAt = useRef(0);
  // The clock running out and the last answer can both end the round; only the first counts.
  const finished = useRef(false);

  // A new round (first load, or "Play again") starts from the top. Reset while
  // rendering rather than in an effect, so a tap on Start the instant it
  // appears is not undone by a reset that runs a moment later.
  const [roundFor, setRoundFor] = useState<string | null>(null);
  if (round && round.round_id !== roundFor) {
    setRoundFor(round.round_id);
    setPhase("ready");
    setIndex(0);
    setAnswers([]);
    setStreak(0);
    setFeedback(null);
    finished.current = false;
  }

  const limitMs = (round?.seconds ?? 60) * 1000;
  const statement = round?.statements[index];

  const finish = useCallback(
    (given: RoundAnswer[]) => {
      if (finished.current) return;
      finished.current = true;
      setPhase("submitting");
      void submit({ answers: given }).finally(() => setPhase("done"));
    },
    [submit],
  );

  useEffect(() => {
    if (phase !== "playing") return;
    const timer = setInterval(() => {
      const left = limitMs - (performance.now() - startedAt.current);
      setRemainingMs(Math.max(0, left));
      if (left <= 0) finish(answers.map(({ key, response, time_ms }) => ({ key, response, time_ms })));
    }, 100);
    return () => clearInterval(timer);
  }, [phase, limitMs, answers, finish]);

  function judge(says: boolean) {
    if (phase !== "playing" || !statement || feedback !== null || !round) return;
    const now = performance.now();
    const correct = says === statement.is_true;
    const next = [
      ...answers,
      { key: statement.key, response: says ? "true" : "false", time_ms: Math.round(now - shownAt.current), correct },
    ];
    setAnswers(next);
    setStreak(correct ? streak + 1 : 0);
    setFeedback(correct);
    setTimeout(() => {
      setFeedback(null);
      if (index + 1 >= round.statements.length) {
        finish(next.map(({ key, response, time_ms }) => ({ key, response, time_ms })));
      } else {
        setIndex(index + 1);
        shownAt.current = performance.now();
      }
    }, FEEDBACK_MS);
  }

  // Keyboard: T / right arrow for true, F / left arrow for false.
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (["t", "T", "ArrowRight"].includes(event.key)) judge(true);
      if (["f", "F", "ArrowLeft"].includes(event.key)) judge(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  if (error && !round) return <GameError error={error} backTo={backTo} />;
  if (!round) return <Spinner label="Writing statements..." />;

  if (phase === "done") {
    return result ? (
      <GameResultCard
        result={result}
        backTo={backTo}
        challenge={round.challenge}
        onPlayAgain={load}
        detail={
          <ul className="max-h-64 space-y-2 overflow-y-auto text-left">
            {answers
              .filter((a) => !a.correct)
              .map((a) => {
                const s = round.statements.find((x) => x.key === a.key)!;
                return (
                  <li key={a.key} className="flex items-start gap-2 text-xs text-ink/70">
                    <XCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-red-500" aria-hidden />
                    <span>
                      <span className="font-semibold text-ink">
                        <MathText text={s.subject} />
                      </span>{" "}
                      — {s.is_true ? "this was true" : "this was false"}. <MathText text={s.explanation} />
                    </span>
                  </li>
                );
              })}
          </ul>
        }
      />
    ) : (
      <Alert>{error}</Alert>
    );
  }

  if (phase === "ready") {
    return (
      <GameIntro
        round={round}
        icon={Gauge}
        title="True or False Blitz"
        summary={`${round.seconds} seconds. As many as you can.`}
        onStart={() => {
          startedAt.current = performance.now();
          shownAt.current = performance.now();
          setRemainingMs(limitMs);
          setPhase("playing");
        }}
      >
        <p className="text-sm text-ink/70">
          Each card pairs a term or question with a claim. Decide fast whether it is right. Streaks multiply your
          points, up to three times.
        </p>
      </GameIntro>
    );
  }

  const fraction = remainingMs / limitMs;
  const score = answers.filter((a) => a.correct).length;

  return (
    <div className="mx-auto max-w-xl">
      <div className="mb-3 flex items-center justify-between text-sm">
        <span className="font-semibold text-ink/60">{Math.ceil(remainingMs / 1000)}s left</span>
        <span className="flex items-center gap-3">
          {streak >= 3 && (
            <span className="flex animate-pop items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-xs font-bold text-red-700">
              <Flame className="h-3.5 w-3.5 fill-orange-400 text-red-500" aria-hidden /> {streak}
            </span>
          )}
          <span className="font-bold text-ink">
            {score} right of {answers.length}
          </span>
        </span>
      </div>
      <div className="mb-4 h-2.5 overflow-hidden rounded-full bg-ink/10" aria-hidden>
        <div
          className={`h-full rounded-full transition-[width] duration-100 ease-linear ${
            fraction > 0.5 ? "bg-green-500" : fraction > 0.2 ? "bg-gold" : "bg-red-500"
          }`}
          style={{ width: `${fraction * 100}%` }}
        />
      </div>

      {statement && (
        <div
          key={statement.key}
          className={[
            "card animate-fade-in p-6 text-center",
            feedback === true ? "border-green-400" : feedback === false ? "animate-shake border-red-400" : "",
          ].join(" ")}
        >
          {/* Not uppercased: capitals would corrupt maths ("dx" is not "DX"). */}
          <p className="text-sm font-semibold text-ink/55">
            <MathText text={statement.subject} />
          </p>
          <p className="mt-3 text-lg font-semibold leading-snug text-ink">
            <MathText text={statement.claim} />
          </p>
          {feedback !== null && (
            <p className={`mt-3 flex items-center justify-center gap-1 text-sm font-bold ${feedback ? "text-green-700" : "text-red-600"}`}>
              {feedback ? <CheckCircle2 className="h-4 w-4" aria-hidden /> : <XCircle className="h-4 w-4" aria-hidden />}
              {feedback ? "Right" : statement.is_true ? "It was true" : "It was false"}
            </p>
          )}
        </div>
      )}

      <div className="mt-5 grid grid-cols-2 gap-3">
        <button
          type="button"
          onClick={() => judge(false)}
          disabled={phase !== "playing"}
          className="flex items-center justify-center gap-2 rounded-2xl border-2 border-red-300 bg-red-50 py-5 text-lg font-bold text-red-700 transition active:scale-95"
        >
          <X className="h-6 w-6" aria-hidden /> False
        </button>
        <button
          type="button"
          onClick={() => judge(true)}
          disabled={phase !== "playing"}
          className="flex items-center justify-center gap-2 rounded-2xl border-2 border-green-400 bg-green-50 py-5 text-lg font-bold text-green-800 transition active:scale-95"
        >
          <Check className="h-6 w-6" aria-hidden /> True
        </button>
      </div>
      <p className="mt-3 hidden text-center text-xs text-ink/40 sm:block">Keys: F or ← for false, T or → for true</p>
      {phase === "submitting" && <Spinner label="Saving your score..." />}
    </div>
  );
}
