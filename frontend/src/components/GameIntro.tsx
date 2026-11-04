import { ArrowLeft, LucideIcon, Swords } from "lucide-react";
import { ReactNode } from "react";
import { Link } from "react-router-dom";

import { RoundBase } from "../api/games";
import { Alert } from "./ui";

/** The screen before play: what the game is, the score to beat, and Start. */
export function GameIntro({
  round,
  icon: Icon,
  title,
  summary,
  children,
  onStart,
}: {
  round: RoundBase;
  icon: LucideIcon;
  title: string;
  summary: string;
  children?: ReactNode;
  onStart: () => void;
}) {
  return (
    <div className="mx-auto max-w-md text-center">
      <div className="card overflow-hidden">
        <div className="bg-gradient-to-br from-navy to-navy-light p-8 text-white">
          <Icon className="mx-auto h-12 w-12 text-gold" aria-hidden />
          <h1 className="mt-3 text-2xl font-bold">{title}</h1>
          <p className="mt-1 text-sm text-white/70">{summary}</p>
          {round.challenge && <p className="mt-2 text-xs text-white/50">{round.title}</p>}
        </div>
        <div className="space-y-3 p-5">
          {children}
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
          <button type="button" onClick={onStart} className="btn-gold w-full py-3 text-base">
            Start
          </button>
        </div>
      </div>
    </div>
  );
}

/** Shown when a round cannot be dealt: usually not enough material yet. */
export function GameError({ error, backTo }: { error: string; backTo: string }) {
  return (
    <div className="mx-auto max-w-md space-y-3">
      <Alert>{error}</Alert>
      <Link to={backTo} className="btn-secondary">
        <ArrowLeft className="h-4 w-4" aria-hidden /> Back
      </Link>
    </div>
  );
}
