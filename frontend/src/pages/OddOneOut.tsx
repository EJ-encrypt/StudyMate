import { ArrowRight, CheckCircle2, Shapes, XCircle } from "lucide-react";
import { useRef, useState } from "react";

import { OddRound, RoundAnswer } from "../api/games";
import GameResultCard from "../components/GameResultCard";
import { GameError, GameIntro } from "../components/GameIntro";
import MathText from "../components/MathText";
import { Alert, Spinner } from "../components/ui";
import { useArcadeRound } from "../lib/useArcadeRound";

/** Odd One Out: three concepts belong together, one does not. */
export default function OddOneOut() {
  const { round, result, error, load, submit, backTo } = useArcadeRound<OddRound>("odd-one-out");
  const [phase, setPhase] = useState<"ready" | "playing" | "submitting" | "done">("ready");
  const [index, setIndex] = useState(0);
  const [chosen, setChosen] = useState<string | null>(null);
  const [answers, setAnswers] = useState<RoundAnswer[]>([]);
  const shownAt = useRef(0);

  // A new round (first load, or "Play again") starts from the top. Reset while
  // rendering rather than in an effect, so a tap on Start the instant it
  // appears is not undone by a reset that runs a moment later.
  const [roundFor, setRoundFor] = useState<string | null>(null);
  if (round && round.round_id !== roundFor) {
    setRoundFor(round.round_id);
    setPhase("ready");
    setIndex(0);
    setChosen(null);
    setAnswers([]);
  }

  if (error && !round) return <GameError error={error} backTo={backTo} />;
  if (!round) return <Spinner label="Sorting concepts into groups..." />;

  const puzzle = round.puzzles[index];
  const correctSoFar = answers.filter((a, i) => a.response === round.puzzles[i].odd_id).length;

  function pick(conceptId: string) {
    if (chosen || phase !== "playing") return;
    setChosen(conceptId);
    setAnswers((prev) => [
      ...prev,
      { key: String(index), response: conceptId, time_ms: Math.round(performance.now() - shownAt.current) },
    ]);
  }

  function next() {
    if (!round || phase !== "playing") return;
    if (index + 1 >= round.puzzles.length) {
      setPhase("submitting");
      void submit({ answers }).finally(() => setPhase("done"));
      return;
    }
    setIndex(index + 1);
    setChosen(null);
    shownAt.current = performance.now();
  }

  if (phase === "done") {
    return result ? (
      <GameResultCard result={result} backTo={backTo} challenge={round.challenge} onPlayAgain={load} />
    ) : (
      <Alert>{error}</Alert>
    );
  }

  if (phase === "ready") {
    return (
      <GameIntro
        round={round}
        icon={Shapes}
        title="Odd One Out"
        summary={`${round.puzzles.length} puzzle${round.puzzles.length === 1 ? "" : "s"}. Spot the one that does not belong.`}
        onStart={() => {
          shownAt.current = performance.now();
          setPhase("playing");
        }}
      >
        <p className="text-sm text-ink/70">
          Each puzzle shows four concepts. Three are closely related; tap the one that is not. Quick answers earn a
          bonus.
        </p>
      </GameIntro>
    );
  }

  const answered = chosen !== null;
  const right = chosen === puzzle.odd_id;

  return (
    <div className="mx-auto max-w-xl">
      <div className="mb-3 flex items-center justify-between text-sm">
        <span className="font-semibold text-ink/60">
          Puzzle {index + 1} of {round.puzzles.length}
        </span>
        <span className="font-bold text-ink">{correctSoFar} right</span>
      </div>
      <div className="mb-4 h-1.5 overflow-hidden rounded-full bg-ink/10" aria-hidden>
        <div className="h-full rounded-full bg-gold transition-all" style={{ width: `${(index / round.puzzles.length) * 100}%` }} />
      </div>

      <p className="mb-3 text-center text-sm font-semibold text-ink">Which one does not belong?</p>
      <div key={index} className="grid animate-fade-in grid-cols-2 gap-3">
        {puzzle.options.map((option) => {
          const isOdd = option.concept_id === puzzle.odd_id;
          const isChosen = option.concept_id === chosen;
          return (
            <button
              key={option.concept_id}
              type="button"
              onClick={() => pick(option.concept_id)}
              disabled={answered}
              className={[
                "flex min-h-[6rem] flex-col items-center justify-center rounded-2xl border-2 p-3 text-center text-sm font-semibold transition",
                answered && isOdd
                  ? "border-green-400 bg-green-50 text-green-900"
                  : answered && isChosen
                    ? "animate-shake border-red-400 bg-red-50 text-red-700"
                    : answered
                      ? "border-ink/10 bg-surface text-ink/60"
                      : "border-ink/10 bg-surface text-ink hover:-translate-y-0.5 hover:border-gold hover:shadow-lift active:scale-[0.98]",
              ].join(" ")}
            >
              <MathText text={option.name} />
            </button>
          );
        })}
      </div>

      {answered && (
        <div className="card mt-4 animate-fade-in p-4">
          <p className={`flex items-center gap-1.5 text-sm font-bold ${right ? "text-green-700" : "text-red-600"}`}>
            {right ? <CheckCircle2 className="h-4 w-4" aria-hidden /> : <XCircle className="h-4 w-4" aria-hidden />}
            {right ? "Spot on." : "Not quite."} The other three all relate to {puzzle.theme}.
          </p>
          <ul className="mt-2 space-y-1.5 text-xs text-ink/70">
            {puzzle.options.map((option) => (
              <li key={option.concept_id}>
                <span className="font-semibold text-ink">{option.name}</span>
                {option.concept_id === puzzle.odd_id && <span className="text-gold-dark"> (the odd one)</span>}:{" "}
                <MathText text={option.summary} />
              </li>
            ))}
          </ul>
          <button type="button" onClick={next} className="btn-primary mt-3 w-full">
            {index + 1 >= round.puzzles.length ? "See results" : "Next puzzle"} <ArrowRight className="h-4 w-4" aria-hidden />
          </button>
        </div>
      )}
      {phase === "submitting" && <Spinner label="Saving your score..." />}
    </div>
  );
}
