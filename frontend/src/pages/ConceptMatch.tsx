import { ArrowLeft, Grid3x3, HelpCircle, Lightbulb, Timer, XCircle } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { errorMessage } from "../api/client";
import { GameResult, MatchRound, startConceptMatch, submitConceptMatch } from "../api/games";
import GameResultCard from "../components/GameResultCard";
import { Alert, Spinner } from "../components/ui";

interface Card {
  key: string;
  conceptId: string;
  kind: "name" | "clue";
  text: string;
}

const MISMATCH_MS = 900;

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
  const [cards, setCards] = useState<Card[]>([]);
  const [flipped, setFlipped] = useState<string[]>([]);
  const [matched, setMatched] = useState<Set<string>>(new Set());
  const [wrongPair, setWrongPair] = useState<string[]>([]);
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
    setFlipped([]);
    setMatched(new Set());
    setMistakes(0);
    setElapsed(0);
    startedAt.current = null;
    startConceptMatch(courseId)
      .then((data) => {
        setRound(data);
        setCards(
          shuffle(
            data.pairs.flatMap((pair) => [
              { key: `${pair.concept_id}-name`, conceptId: pair.concept_id, kind: "name" as const, text: pair.name },
              { key: `${pair.concept_id}-clue`, conceptId: pair.concept_id, kind: "clue" as const, text: pair.clue },
            ]),
          ),
        );
      })
      .catch((err) => setError(errorMessage(err, "Could not start a round.")));
  }, [courseId]);

  useEffect(load, [load]);

  const finished = round !== null && matched.size === round.pairs.length;

  // The clock starts on the first flip, so reading the rules is free.
  useEffect(() => {
    if (startedAt.current === null || finished) return;
    const timer = setInterval(() => setElapsed(performance.now() - startedAt.current!), 250);
    return () => clearInterval(timer);
  }, [flipped, finished]);

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

  function flip(card: Card) {
    if (matched.has(card.conceptId) || flipped.includes(card.key) || flipped.length === 2) return;
    if (startedAt.current === null) startedAt.current = performance.now();

    const next = [...flipped, card.key];
    setFlipped(next);
    if (next.length < 2) return;

    const [first, second] = next.map((key) => cards.find((c) => c.key === key)!);
    if (first.conceptId === second.conceptId) {
      setMatched((prev) => new Set(prev).add(first.conceptId));
      setFlipped([]);
    } else {
      setMistakes((n) => n + 1);
      setWrongPair(next);
      setTimeout(() => {
        setFlipped([]);
        setWrongPair([]);
      }, MISMATCH_MS);
    }
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
          <p className="text-sm text-navy/60">
            {formatTime(elapsed)} · {mistakes} wrong pair{mistakes === 1 ? "" : "s"}
          </p>
        }
      />
    );
  }

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-gold text-navy">
            <Grid3x3 className="h-5 w-5" aria-hidden />
          </span>
          <div>
            <h1 className="text-lg font-bold leading-tight text-navy">Concept Match</h1>
            <p className="text-xs text-navy/55">Pair each concept with its meaning.</p>
          </div>
        </div>
        <div className="flex items-center gap-4 text-sm font-semibold text-navy">
          <span className="flex items-center gap-1">
            <Timer className="h-4 w-4 text-navy/50" aria-hidden /> {formatTime(elapsed)}
          </span>
          <span className="flex items-center gap-1">
            <Lightbulb className="h-4 w-4 text-gold-dark" aria-hidden /> {matched.size}/{round.pairs.length}
          </span>
          <span className="flex items-center gap-1">
            <XCircle className="h-4 w-4 text-red-400" aria-hidden /> {mistakes}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 sm:gap-3">
        {cards.map((card) => {
          const isMatched = matched.has(card.conceptId);
          const isUp = isMatched || flipped.includes(card.key);
          const isWrong = wrongPair.includes(card.key);
          return (
            <button
              key={card.key}
              type="button"
              onClick={() => flip(card)}
              disabled={isMatched}
              aria-label={isUp ? card.text : "Hidden card"}
              className={[
                "flex aspect-[3/4] items-center justify-center rounded-xl border-2 p-2 text-center transition sm:aspect-[4/5] sm:p-3",
                isMatched
                  ? "animate-pop border-green-400 bg-green-50"
                  : isWrong
                    ? "animate-shake border-red-300 bg-red-50"
                    : isUp
                      ? card.kind === "name"
                        ? "border-navy bg-navy text-white"
                        : "border-gold bg-gold/10"
                      : "border-navy/10 bg-gradient-to-br from-navy to-navy-light hover:-translate-y-0.5 hover:shadow-lift",
              ].join(" ")}
            >
              {isUp ? (
                <span
                  className={[
                    card.kind === "name" ? "text-xs font-bold sm:text-sm" : "text-[10px] leading-snug sm:text-xs",
                    isMatched ? "text-green-900" : card.kind === "name" ? "text-white" : "text-navy",
                  ].join(" ")}
                >
                  {card.text}
                </span>
              ) : (
                <HelpCircle className="h-6 w-6 text-gold/70" aria-hidden />
              )}
            </button>
          );
        })}
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
