import { CheckCircle2, Heart, HeartCrack, Shield, XCircle } from "lucide-react";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";

import { RoundAnswer, StrikesRound } from "../api/games";
import GameResultCard from "../components/GameResultCard";
import { GameError, GameIntro } from "../components/GameIntro";
import MathText from "../components/MathText";
import { Alert, Spinner } from "../components/ui";
import { useArcadeRound } from "../lib/useArcadeRound";

const FEEDBACK_MS = 1100;

// Mirrors app.services.arcade on the server, which has the final say.
const secondsFor = (correct: number) => Math.max(7, 20 - Math.floor(correct / 3) * 2);
const levelFor = (correct: number) => 1 + Math.floor(correct / 5);

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

/** Three Strikes: keep answering until your third mistake. It gets faster as you go. */
export default function ThreeStrikes() {
  const { round, result, error, load, submit, backTo } = useArcadeRound<StrikesRound>("three-strikes");
  const [phase, setPhase] = useState<"ready" | "playing" | "feedback" | "submitting" | "done">("ready");
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<(RoundAnswer & { correct: boolean })[]>([]);
  const [typed, setTyped] = useState("");
  const [remainingMs, setRemainingMs] = useState(0);
  const shownAt = useRef(0);
  const answered = useRef(false);

  // A new round (first load, or "Play again") starts from the top. Reset while
  // rendering rather than in an effect, so a tap on Start the instant it
  // appears is not undone by a reset that runs a moment later.
  const [roundFor, setRoundFor] = useState<string | null>(null);
  if (round && round.round_id !== roundFor) {
    setRoundFor(round.round_id);
    setPhase("ready");
    setIndex(0);
    setAnswers([]);
  }

  const correct = answers.filter((a) => a.correct).length;
  const strikes = answers.length - correct;
  const allowed = (round?.strikes ?? 3) - strikes;
  const limitMs = secondsFor(correct) * 1000;
  const question = round?.questions[index];
  const last = answers[answers.length - 1];

  function show() {
    answered.current = false;
    setTyped("");
    shownAt.current = performance.now();
    setRemainingMs(limitMs);
    setPhase("playing");
  }

  const answer = useCallback(
    (response: string) => {
      if (!question || answered.current) return;
      answered.current = true;
      const timeMs = Math.round(performance.now() - shownAt.current);
      const isRight = timeMs <= limitMs && !!response && normalize(response) === normalize(question.answer);
      setAnswers((prev) => [...prev, { key: question.item_id, response, time_ms: timeMs, correct: isRight }]);
      setPhase("feedback");
    },
    [question, limitMs],
  );

  useEffect(() => {
    if (phase !== "playing") return;
    const timer = setInterval(() => {
      const left = limitMs - (performance.now() - shownAt.current);
      setRemainingMs(Math.max(0, left));
      if (left <= 0) answer("");
    }, 100);
    return () => clearInterval(timer);
  }, [phase, limitMs, answer]);

  useEffect(() => {
    if (phase !== "feedback" || !round) return;
    const timer = setTimeout(() => {
      const out = strikes >= round.strikes;
      const exhausted = index + 1 >= round.questions.length;
      if (out || exhausted) {
        setPhase("submitting");
        void submit({ answers: answers.map(({ key, response, time_ms }) => ({ key, response, time_ms })) }).finally(
          () => setPhase("done"),
        );
      } else {
        setIndex(index + 1);
        show();
      }
    }, FEEDBACK_MS);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase]);

  if (error && !round) return <GameError error={error} backTo={backTo} />;
  if (!round) return <Spinner label="Lining up questions..." />;

  if (phase === "done") {
    return result ? (
      <GameResultCard
        result={result}
        backTo={backTo}
        challenge={round.challenge}
        onPlayAgain={load}
        detail={
          <p className="text-sm text-ink/60">
            {correct} answered before the third strike
            {correct === round.questions.length ? " — you cleared every question!" : "."}
          </p>
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
        icon={Shield}
        title="Three Strikes"
        summary="Keep going until your third mistake."
        onStart={show}
      >
        <p className="text-sm text-ink/70">
          You start with 20 seconds a question, and lose two seconds every three right answers. Points rise every
          five in a row. Recall questions come later, when it is hardest.
        </p>
      </GameIntro>
    );
  }

  const fraction = remainingMs / limitMs;
  const showing = phase === "feedback" && last;

  function submitTyped(event: FormEvent) {
    event.preventDefault();
    if (typed.trim()) answer(typed.trim());
  }

  return (
    <div className="mx-auto max-w-xl">
      <div className="mb-3 flex items-center justify-between text-sm">
        <span className="flex items-center gap-1" aria-label={`${allowed} lives left`}>
          {Array.from({ length: round.strikes }, (_, i) =>
            i < allowed ? (
              <Heart key={i} className="h-5 w-5 fill-red-500 text-red-500" aria-hidden />
            ) : (
              <HeartCrack key={i} className="h-5 w-5 text-ink/25" aria-hidden />
            ),
          )}
        </span>
        <span className="flex items-center gap-3">
          <span className="rounded-full bg-gold/20 px-2 py-0.5 text-xs font-bold text-ink">Level {levelFor(correct)}</span>
          <span className="font-bold text-ink">{correct} right</span>
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

      {question && (
        <div
          className={[
            "card p-5",
            showing ? (last.correct ? "border-green-400" : "animate-shake border-red-300") : "",
          ].join(" ")}
        >
          <p className="text-xs font-semibold text-ink/45">{secondsFor(correct)} seconds</p>
          <p className="mt-1 text-lg font-semibold leading-snug text-ink">
            <MathText text={question.question} />
          </p>
          {question.options.length > 0 ? (
            <div className="mt-5 grid gap-2.5 sm:grid-cols-2">
              {question.options.map((option) => {
                const isAnswer = normalize(option) === normalize(question.answer);
                const chosen = showing && last.response === option;
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
                placeholder="Type the answer"
                className="input"
              />
              <button type="submit" disabled={phase !== "playing" || !typed.trim()} className="btn-primary">
                Go
              </button>
            </form>
          )}
          {showing && (
            <p className={`mt-4 flex items-center gap-1.5 text-sm font-semibold ${last.correct ? "text-green-700" : "text-red-600"}`}>
              {last.correct ? <CheckCircle2 className="h-4 w-4" aria-hidden /> : <XCircle className="h-4 w-4" aria-hidden />}
              {last.correct ? (
                `+${100 * levelFor(correct - 1)}`
              ) : (
                <>
                  Strike {strikes}! It was: <MathText text={question.answer} />
                </>
              )}
            </p>
          )}
        </div>
      )}
      {phase === "submitting" && <Spinner label="Saving your score..." />}
    </div>
  );
}
