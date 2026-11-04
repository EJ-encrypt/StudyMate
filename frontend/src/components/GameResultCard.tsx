import { ArrowLeft, PartyPopper, RotateCcw, Trophy, Zap } from "lucide-react";
import { ReactNode } from "react";
import { Link } from "react-router-dom";

import { GameResult } from "../api/games";
import { NewBadges } from "./ui";

/** End-of-round screen shared by both games. */
export default function GameResultCard({
  result,
  courseId,
  onPlayAgain,
  detail,
}: {
  result: GameResult;
  courseId: string;
  onPlayAgain: () => void;
  detail?: ReactNode;
}) {
  return (
    <div className="mx-auto max-w-md animate-pop">
      <div className="card overflow-hidden text-center">
        <div className="bg-gradient-to-br from-navy to-navy-light px-6 pb-6 pt-8 text-white">
          <span className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-gold/20 text-gold">
            {result.is_personal_best ? (
              <PartyPopper className="h-8 w-8" aria-hidden />
            ) : (
              <Trophy className="h-8 w-8" aria-hidden />
            )}
          </span>
          <p className="mt-3 text-sm font-semibold uppercase tracking-wide text-gold">
            {result.is_personal_best ? "New personal best!" : "Round complete"}
          </p>
          <p className="mt-1 text-5xl font-extrabold tracking-tight">{result.score.toLocaleString()}</p>
          <p className="mt-1 text-sm text-white/60">Best: {result.personal_best.toLocaleString()}</p>
        </div>
        <div className="grid grid-cols-2 divide-x divide-ink/5 border-b border-ink/5">
          <div className="p-3">
            <p className="text-xs text-ink/55">Correct</p>
            <p className="text-lg font-bold text-ink">
              {result.correct}/{result.total}
            </p>
          </div>
          <div className="p-3">
            <p className="text-xs text-ink/55">XP earned</p>
            <p className="flex items-center justify-center gap-1 text-lg font-bold text-ink">
              <Zap className="h-4 w-4 text-gold-dark" aria-hidden />+{result.xp_awarded}
            </p>
          </div>
        </div>
        <div className="space-y-3 p-4">
          {detail}
          <NewBadges badges={result.new_badges} />
          <div className="flex gap-2">
            <Link to={`/play?course=${courseId}`} className="btn-secondary flex-1">
              <ArrowLeft className="h-4 w-4" aria-hidden /> Arcade
            </Link>
            <button type="button" onClick={onPlayAgain} className="btn-primary flex-1">
              <RotateCcw className="h-4 w-4" aria-hidden /> Play again
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
