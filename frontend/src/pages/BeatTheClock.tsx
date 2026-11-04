import { ArrowLeft, CheckCircle2, Flame, Swords, Timer, XCircle } from "lucide-react";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { ClockRound } from "../api/games";
import GameResultCard from "../components/GameResultCard";
import { useArcadeRound } from "../lib/useArcadeRound";
import MathText from "../components/MathText";
import { Alert, Spinner } from "../components/ui";

type Phase = "loading" | "ready" | "countdown" | "playing" | "feedback" | "submitting" | "done";

interface Answer {
  item_id: string;
  response: string;
  time_ms: number;
  correct: boolean;
}

const FEEDBACK_MS = 1200;

/** Mirrors the server's marking closely enough for instant feedback; the server's verdict is final. */
function normalize(text: string): string {
  return text
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^\w\s]/g, " ")
    .split(/\s+/)
    .filter((word) => word && !["a", "an", "the"].includes(word))
    .join(" ");
}

function points(timeMs: number, limitMs: number, streak: number): number {
  const remaining = Math.max(0, limitMs - Math.min(Math.max(timeMs, 0), limitMs));
  const multiplier = Math.min(1 + 0.25 * (streak - 1), 2);
  return Math.round((100 + Math.round((100 * remaining) / limitMs)) * multiplier);
}

export default function BeatTheClock() {
  const { round, result, error, load, submit, backTo } = useArcadeRound<ClockRound>("beat-the-clock");
  const [phase, setPhase] = useState<Phase>("loading");
  const [countdown, setCountdown] = useState(3);
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<Answer[]>([]);
  const [typed, setTyped] = useState("");
  const [remainingMs, setRemainingMs] = useState(0);
  const [score, setScore] = useState(0);
  const [streak, setStreak] = useState(0);
  const startedAt = useRef(0);
  const answeredRef = useRef(false);

  const limitMs = (round?.seconds_per_question ?? 15) * 1000;
  const question = round?.questions[index];
  const lastAnswer = answers[answers.length - 1];

  // A new round (first load, or "Play again") starts from the top. Reset while
  // rendering rather than in an effect, so a tap on Start the instant it
  // appears is not undone by a reset that runs a moment later.
  const [roundFor, setRoundFor] = useState<string | null>(null);
  if (round && round.round_id !== roundFor) {
    setRoundFor(round.round_id);
    setAnswers([]);
    setIndex(0);
    setScore(0);
    setStreak(0);
    setPhase("ready");
  }
  if (!round && phase !== "loading") setPhase("loading");

  // 3-2-1 before the first question.
  useEffect(() => {
    if (phase !== "countdown") return;
    if (countdown === 0) {
      beginQuestion();
      return;
    }
    const timer = setTimeout(() => setCountdown((n) => n - 1), 700);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase, countdown]);

  function beginQuestion() {
    answeredRef.current = false;
    setTyped("");
    startedAt.current = performance.now();
    setRemainingMs(limitMs);
    setPhase("playing");
  }

  const answer = useCallback(
    (response: string) => {
      if (!question || answeredRef.current) return;
      answeredRef.current = true;
      const timeMs = Math.round(performance.now() - startedAt.current);
      const correct = timeMs <= limitMs && !!response && normalize(response) === normalize(question.answer);
      const nextStreak = correct ? streak + 1 : 0;
      setStreak(nextStreak);
      if (correct) setScore((s) => s + points(timeMs, limitMs, nextStreak));
      setAnswers((prev) => [...prev, { item_id: question.item_id, response, time_ms: timeMs, correct }]);
      setPhase("feedback");
    },
    [question, limitMs, streak],
  );

  // The countdown bar, and running out of time.
  useEffect(() => {
    if (phase !== "playing") return;
    const timer = setInterval(() => {
      const left = limitMs - (performance.now() - startedAt.current);
      setRemainingMs(Math.max(0, left));
      if (left <= 0) answer("");
    }, 100);
    return () => clearInterval(timer);
  }, [phase, limitMs, answer]);

  // After feedback, the next question or the end of the round.
  useEffect(() => {
    if (phase !== "feedback" || !round) return;
    const timer = setTimeout(() => {
      if (index + 1 < round.questions.length) {
        setIndex((i) => i + 1);
        beginQuestion();
      } else {
        setPhase("submitting");
        void submit({
          answers: answers.map(({ item_id, response, time_ms }) => ({ key: item_id, response, time_ms })),
        }).finally(() => setPhase("done"));
      }
    }, FEEDBACK_MS);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase]);

  function submitTyped(event: FormEvent) {
    event.preventDefault();
    if (typed.trim()) answer(typed.trim());
  }

  if (error && !round) {
    return (
      <div className="mx-auto max-w-md space-y-3">
        <Alert>{error}</Alert>
        <Link to={backTo} className="btn-secondary">
          <ArrowLeft className="h-4 w-4" aria-hidden /> Back to the Arcade
        </Link>
      </div>
    );
  }
  if (phase === "loading" || !round) return <Spinner label="Shuffling questions..." />;

  if (phase === "done") {
    return result ? (
      <GameResultCard
        result={result}
        backTo={backTo}
        challenge={round.challenge}
        onPlayAgain={load}
        detail={
          <ul className="space-y-1.5 text-left">
            {round.questions.map((q, i) => {
              const ok = result.answers[i]?.correct;
              return (
                <li key={q.item_id} className="flex items-start gap-2 text-xs text-ink/70">
                  {ok ? (
                    <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-green-600" aria-hidden />
                  ) : (
                    <XCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-red-500" aria-hidden />
                  )}
                  <span>
                    <MathText text={q.question} className="text-ink" />
                    {!ok && (
                      <span className="block font-semibold text-ink">
                        → <MathText text={q.answer} />
                      </span>
                    )}
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

  if (phase === "ready" || phase === "countdown") {
    return (
      <div className="mx-auto max-w-md text-center">
        <div className="card overflow-hidden">
          <div className="bg-gradient-to-br from-navy to-navy-light p-8 text-white">
            {phase === "countdown" ? (
              <p key={countdown} className="animate-pop text-7xl font-extrabold text-gold">
                {countdown || "Go!"}
              </p>
            ) : (
              <>
                <Timer className="mx-auto h-12 w-12 text-gold" aria-hidden />
                <h1 className="mt-3 text-2xl font-bold">Beat the Clock</h1>
                <p className="mt-1 text-sm text-white/70">
                  {round.questions.length} questions · {round.seconds_per_question}s each
                </p>
              </>
            )}
          </div>
          {phase === "ready" && (
            <div className="space-y-3 p-5">
              <p className="text-sm text-ink/70">
                Answer fast for bonus points. Get several right in a row to multiply your score.
              </p>
              {round.challenge ? (
                <p className="flex items-center justify-center gap-1.5 rounded-lg bg-gold/15 px-3 py-2 text-sm font-semibold text-ink">
                  <Swords className="h-4 w-4 text-gold-dark" aria-hidden />
                  Beat {round.challenge.challenger_name}: {round.challenge.challenger_score.toLocaleString()}
                </p>
              ) : (
                round.personal_best !== null && (
                  <p className="text-xs text-ink/50">Your best: {round.personal_best.toLocaleString()}</p>
                )
              )}
              <button
                type="button"
                onClick={() => {
                  setCountdown(3);
                  setPhase("countdown");
                }}
                className="btn-gold w-full py-3 text-base"
              >
                Start
              </button>
            </div>
          )}
        </div>
      </div>
    );
  }

  const fraction = remainingMs / limitMs;
  const showing = phase === "feedback" && lastAnswer;

  return (
    <div className="mx-auto max-w-xl">
      <div className="mb-3 flex items-center justify-between text-sm">
        <span className="font-semibold text-ink/60">
          Question {index + 1} of {round.questions.length}
        </span>
        <span className="flex items-center gap-3">
          {streak >= 2 && (
            <span className="flex animate-pop items-center gap-1 rounded-full bg-gold/25 px-2 py-0.5 text-xs font-bold text-ink">
              <Flame className="h-3.5 w-3.5 text-gold-dark" aria-hidden /> {streak} in a row
            </span>
          )}
          <span className="font-bold text-ink">{score.toLocaleString()}</span>
        </span>
      </div>

      <div className="mb-4 h-2.5 overflow-hidden rounded-full bg-ink/10" aria-hidden>
        <div
          className={`h-full rounded-full transition-[width] duration-100 ease-linear ${
            fraction > 0.5 ? "bg-green-500" : fraction > 0.25 ? "bg-gold" : "bg-red-500"
          }`}
          style={{ width: `${(phase === "playing" ? fraction : 0) * 100}%` }}
        />
      </div>

      <div
        className={[
          "card p-5",
          showing ? (lastAnswer.correct ? "border-green-400" : "animate-shake border-red-300") : "",
        ].join(" ")}
      >
        <p className="text-lg font-semibold leading-snug text-ink">
          <MathText text={question?.question ?? ""} />
        </p>

        {question && question.options.length > 0 ? (
          <div className="mt-5 grid gap-2.5 sm:grid-cols-2">
            {question.options.map((option) => {
              const isAnswer = normalize(option) === normalize(question.answer);
              const chosen = showing && lastAnswer.response === option;
              return (
                <button
                  key={option}
                  type="button"
                  disabled={phase !== "playing"}
                  onClick={() => answer(option)}
                  className={[
                    "rounded-xl border-2 px-4 py-3 text-left text-sm font-semibold transition",
                    showing && isAnswer
                      ? "border-green-500 bg-green-50 text-green-800"
                      : chosen
                        ? "border-red-400 bg-red-50 text-red-700"
                        : "border-ink/10 bg-surface text-ink hover:border-gold hover:bg-gold/10 active:scale-[0.98]",
                  ].join(" ")}
                >
                  <MathText text={option} />
                </button>
              );
            })}
          </div>
        ) : (
          <form onSubmit={submitTyped} className="mt-5 flex gap-2">
            <input
              autoFocus
              value={typed}
              disabled={phase !== "playing"}
              onChange={(e) => setTyped(e.target.value)}
              placeholder="Type the missing term"
              className="input"
            />
            <button type="submit" disabled={phase !== "playing" || !typed.trim()} className="btn-primary">
              Go
            </button>
          </form>
        )}

        {showing && (
          <p
            className={`mt-4 flex items-center gap-1.5 text-sm font-semibold ${lastAnswer.correct ? "text-green-700" : "text-red-600"}`}
          >
            {lastAnswer.correct ? (
              <CheckCircle2 className="h-4 w-4" aria-hidden />
            ) : (
              <XCircle className="h-4 w-4" aria-hidden />
            )}
            {lastAnswer.correct
              ? `+${points(lastAnswer.time_ms, limitMs, streak)}`
              : lastAnswer.response
                ? <>It was: <MathText text={question?.answer ?? ""} /></>
                : <>Time's up! It was: <MathText text={question?.answer ?? ""} /></>}
          </p>
        )}
      </div>

      {phase === "submitting" && <Spinner label="Saving your score..." />}
    </div>
  );
}
