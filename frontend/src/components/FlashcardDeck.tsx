import { ArrowLeft, ArrowRight, CheckCircle2, RotateCw, Shuffle } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { AssessmentItem } from "../api/assessments";
import MathText from "./MathText";

interface Card {
  item: AssessmentItem;
  /** Show the term first and recall the definition, or the reverse. */
  termFirst: boolean;
}

function shuffled<T>(items: T[]): T[] {
  const copy = [...items];
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

/**
 * Half the cards show the term and half the definition, in a random mix, so
 * the student practises recall in both directions rather than learning to
 * recognise one side.
 */
export function deal(items: AssessmentItem[]): Card[] {
  const directions = shuffled(items.map((_, index) => index % 2 === 0));
  return shuffled(items).map((item, index) => ({ item, termFirst: directions[index] }));
}

function Face({ label, text, hint, back }: { label: string; text: string; hint: string; back?: boolean }) {
  return (
    <div
      className={[
        "flip-face flex min-h-[17rem] flex-col rounded-2xl border p-5 shadow-lift sm:min-h-[19rem] sm:p-7",
        back ? "flip-back border-gold bg-gradient-to-br from-gold/20 to-surface" : "border-ink/10 bg-surface",
      ].join(" ")}
    >
      <span
        className={[
          "w-fit rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide",
          back ? "bg-gold/30 text-ink" : "bg-ink/5 text-ink/60",
        ].join(" ")}
      >
        {label}
      </span>
      <div className="flex flex-1 items-center justify-center py-5 text-center">
        <MathText
          text={text}
          className={
            label === "Term" ? "text-xl font-bold leading-snug text-ink sm:text-2xl" : "text-base leading-relaxed text-ink sm:text-lg"
          }
        />
      </div>
      <span className="flex items-center justify-center gap-1.5 text-xs text-ink/45">
        <RotateCw className="h-3.5 w-3.5" aria-hidden /> {hint}
      </span>
    </div>
  );
}

export default function FlashcardDeck({ items }: { items: AssessmentItem[] }) {
  const [cards, setCards] = useState(() => deal(items));
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [finished, setFinished] = useState(false);

  const card = cards[index];

  const go = useCallback(
    (step: number) => {
      const next = index + step;
      if (next >= cards.length) {
        setFinished(true);
        return;
      }
      if (next < 0) return;
      setFlipped(false);
      setIndex(next);
    },
    [cards.length, index],
  );

  function restart() {
    setCards(deal(items));
    setIndex(0);
    setFlipped(false);
    setFinished(false);
  }

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (finished || event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return;
      if (event.key === " " || event.key === "Enter") {
        event.preventDefault();
        setFlipped((value) => !value);
      } else if (event.key === "ArrowRight") {
        go(1);
      } else if (event.key === "ArrowLeft") {
        go(-1);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [finished, go]);

  if (cards.length === 0) return null;

  if (finished) {
    return (
      <div className="card mx-auto mt-6 flex max-w-md animate-pop flex-col items-center p-8 text-center">
        <span className="flex h-14 w-14 items-center justify-center rounded-full bg-green-100 text-green-700">
          <CheckCircle2 className="h-7 w-7" aria-hidden />
        </span>
        <p className="mt-3 text-lg font-bold text-ink">Deck complete</p>
        <p className="mt-1 text-sm text-ink/60">
          You went through all {cards.length} cards. Go again and they come back in a new order, with sides mixed
          differently.
        </p>
        <button type="button" onClick={restart} className="btn-primary mt-5">
          <Shuffle className="h-4 w-4" aria-hidden /> Shuffle and go again
        </button>
      </div>
    );
  }

  const term = card.item.question;
  const definition = card.item.answer ?? "";
  const front = card.termFirst
    ? { label: "Term", text: term, hint: "Tap to reveal the definition" }
    : { label: "Definition", text: definition, hint: "Tap to reveal the term" };
  const back = card.termFirst
    ? { label: "Definition", text: definition, hint: "Tap to turn back" }
    : { label: "Term", text: term, hint: "Tap to turn back" };

  return (
    <div className="mx-auto mt-6 max-w-xl">
      <div className="mb-3 flex items-center justify-between text-sm">
        <span className="font-semibold text-ink">
          Card {index + 1} <span className="font-normal text-ink/50">of {cards.length}</span>
        </span>
        <span className="text-xs text-ink/50">{card.termFirst ? "Recall the definition" : "Recall the term"}</span>
      </div>
      <div className="mb-4 h-1.5 overflow-hidden rounded-full bg-ink/10" aria-hidden>
        <div className="h-full rounded-full bg-gold transition-all" style={{ width: `${((index + 1) / cards.length) * 100}%` }} />
      </div>

      {/* Keyed by card, so moving on shows the next card face down at once
          instead of animating the old one back over and briefly showing the
          next card's answer. */}
      <button
        key={card.item.id}
        type="button"
        onClick={() => setFlipped((value) => !value)}
        aria-label={flipped ? `${back.label}: ${back.text}. Tap to turn back.` : `${front.label}: ${front.text}. ${front.hint}.`}
        className="flip-scene block w-full animate-fade-in text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-gold focus-visible:ring-offset-2 focus-visible:ring-offset-canvas"
      >
        <div className={`flip-card ${flipped ? "is-flipped" : ""}`}>
          <Face {...front} />
          <Face {...back} back />
        </div>
      </button>

      <div className="mt-5 grid grid-cols-[1fr_auto_1fr] items-center gap-2">
        <button type="button" onClick={() => go(-1)} disabled={index === 0} className="btn-secondary justify-self-start">
          <ArrowLeft className="h-4 w-4" aria-hidden /> Back
        </button>
        <button type="button" onClick={() => setFlipped((value) => !value)} className="btn-ghost">
          <RotateCw className="h-4 w-4" aria-hidden /> Flip
        </button>
        <button type="button" onClick={() => go(1)} className="btn-primary justify-self-end">
          {index === cards.length - 1 ? "Finish" : "Next"} <ArrowRight className="h-4 w-4" aria-hidden />
        </button>
      </div>
      <p className="mt-3 hidden text-center text-xs text-ink/40 sm:block">Space to flip · arrow keys to move</p>
    </div>
  );
}
