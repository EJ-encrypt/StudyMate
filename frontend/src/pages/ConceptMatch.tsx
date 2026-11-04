import { ArrowLeft, CheckCircle2, Link2, Timer, XCircle } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { errorMessage } from "../api/client";
import { GameResult, MatchPair, MatchRound, startConceptMatch, submitConceptMatch } from "../api/games";
import GameResultCard from "../components/GameResultCard";
import MathText from "../components/MathText";
import { Alert, Spinner } from "../components/ui";

type Side = "name" | "clue";

interface Pick {
  side: Side;
  conceptId: string;
}

/** How long a wrong pair stays red before both cards reset. */
const MISMATCH_MS = 750;

function shuffle<T>(items: T[]): T[] {
  const copy = [...items];
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

function formatTime(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

export default function ConceptMatch() {
  const { courseId } = useParams<{ courseId: string }>();
  const [round, setRound] = useState<MatchRound | null>(null);
  // Each column is shuffled on its own, so a concept is rarely level with its meaning.
  const [names, setNames] = useState<MatchPair[]>([]);
  const [clues, setClues] = useState<MatchPair[]>([]);
  const [selected, setSelected] = useState<Pick | null>(null);
  const [matched, setMatched] = useState<Set<string>>(new Set());
  const [wrong, setWrong] = useState<Pick[]>([]);
  const [mistakes, setMistakes] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [result, setResult] = useState<GameResult | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const startedAt = useRef<number | null>(null);

  const load = useCallback(() => {
    if (!courseId) return;
    setRound(null);
    setResult(null);
    setError(null);
    setSelected(null);
    setMatched(new Set());
    setWrong([]);
    setMistakes(0);
    setElapsed(0);
    startedAt.current = null;
    startConceptMatch(courseId)
      .then((data) => {
        setRound(data);
        setNames(shuffle(data.pairs));
        setClues(shuffle(data.pairs));
      })
      .catch((err) => setError(errorMessage(err, "Could not start a round.")));
  }, [courseId]);

  useEffect(load, [load]);

  const finished = round !== null && matched.size === round.pairs.length;

  // The clock starts on the first tap, so reading the cards first is free.
  useEffect(() => {
    if (startedAt.current === null || finished) return;
    const timer = setInterval(() => setElapsed(performance.now() - startedAt.current!), 250);
    return () => clearInterval(timer);
  }, [selected, finished]);

  useEffect(() => {
    if (!finished || !round || !courseId || result || isSubmitting) return;
    const duration = Math.round(performance.now() - (startedAt.current ?? performance.now()));
    setElapsed(duration);
    setIsSubmitting(true);
    submitConceptMatch(
      courseId,
      round.pairs.map((p) => p.concept_id),
      mistakes,
      duration,
    )
      .then(setResult)
      .catch((err) => setError(errorMessage(err, "Could not save your score.")))
      .finally(() => setIsSubmitting(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [finished]);

  function choose(side: Side, conceptId: string) {
    if (matched.has(conceptId) || wrong.length > 0) return;
    if (startedAt.current === null) startedAt.current = performance.now();

    if (!selected || selected.side === side) {
      // First pick, or changing your mind on the same side. Tapping the same
      // card again puts it down.
      setSelected(selected?.side === side && selected.conceptId === conceptId ? null : { side, conceptId });
      return;
    }

    if (selected.conceptId === conceptId) {
      setMatched((prev) => new Set(prev).add(conceptId));
      setSelected(null);
      return;
    }

    setMistakes((n) => n + 1);
    setWrong([selected, { side, conceptId }]);
    setTimeout(() => {
      setWrong([]);
      setSelected(null);
    }, MISMATCH_MS);
  }

  if (error && !round) {
    return (
      <div className="mx-auto max-w-md space-y-3">
        <Alert>{error}</Alert>
        <Link to={`/play?course=${courseId}`} className="btn-secondary">
          <ArrowLeft className="h-4 w-4" aria-hidden /> Back to the Arcade
        </Link>
      </div>
    );
  }
  if (!round) return <Spinner label="Dealing cards..." />;

  if (result) {
    return (
      <GameResultCard
        result={result}
        courseId={round.course_id}
        onPlayAgain={load}
        detail={
          <p className="text-sm text-ink/60">
            {formatTime(elapsed)} · {mistakes} wrong pair{mistakes === 1 ? "" : "s"}
          </p>
        }
      />
    );
  }

  function card(pair: MatchPair, side: Side) {
    const isMatched = matched.has(pair.concept_id);
    const isSelected = selected?.side === side && selected.conceptId === pair.concept_id;
    const isWrong = wrong.some((pick) => pick.side === side && pick.conceptId === pair.concept_id);
    const text = side === "name" ? pair.name : pair.clue;
    return (
      <button
        key={pair.concept_id}
        type="button"
        onClick={() => choose(side, pair.concept_id)}
        disabled={isMatched}
        aria-pressed={isSelected}
        aria-label={`${side === "name" ? "Concept" : "Meaning"}: ${text}${isMatched ? " (matched)" : ""}`}
        className={[
          "flex min-h-[3.5rem] w-full items-center gap-2 rounded-xl border-2 px-3 py-2 text-left transition",
          side === "name" ? "text-sm font-semibold" : "text-xs leading-snug sm:text-sm",
          isMatched
            ? "border-green-400 bg-green-50 text-green-900"
            : isWrong
              ? "animate-shake border-red-400 bg-red-50 text-red-700"
              : isSelected
                ? "border-gold bg-gold/15 text-ink shadow-lift ring-2 ring-gold/40"
                : "border-ink/10 bg-surface text-ink hover:-translate-y-0.5 hover:border-gold/60 hover:shadow-lift",
        ].join(" ")}
      >
        <MathText text={text} className="min-w-0 flex-1 break-words" />
        {isMatched && <CheckCircle2 className="h-4 w-4 shrink-0 text-green-600" aria-hidden />}
      </button>
    );
  }

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-gold text-navy-dark">
            <Link2 className="h-5 w-5" aria-hidden />
          </span>
          <div>
            <h1 className="text-lg font-bold leading-tight text-ink">Concept Match</h1>
            <p className="text-xs text-ink/55">Tap a concept, then the meaning that goes with it.</p>
          </div>
        </div>
        <div className="flex items-center gap-4 text-sm font-semibold text-ink">
          <span className="flex items-center gap-1">
            <Timer className="h-4 w-4 text-ink/50" aria-hidden /> {formatTime(elapsed)}
          </span>
          <span className="flex items-center gap-1">
            <CheckCircle2 className="h-4 w-4 text-green-600" aria-hidden /> {matched.size}/{round.pairs.length}
          </span>
          <span className="flex items-center gap-1">
            <XCircle className="h-4 w-4 text-red-400" aria-hidden /> {mistakes}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-[minmax(0,2fr)_minmax(0,3fr)] gap-2 sm:gap-4">
        <section aria-label="Concepts">
          <h2 className="section-title">Concepts</h2>
          <div className="flex flex-col gap-2">
            {names.map((pair) => card(pair, "name"))}
          </div>
        </section>
        <section aria-label="Meanings">
          <h2 className="section-title">Meanings</h2>
          <div className="flex flex-col gap-2">
            {clues.map((pair) => card(pair, "clue"))}
          </div>
        </section>
      </div>

      {isSubmitting && <Spinner label="Saving your score..." />}
      {error && (
        <div className="mt-4">
          <Alert>{error}</Alert>
        </div>
      )}
    </div>
  );
}
