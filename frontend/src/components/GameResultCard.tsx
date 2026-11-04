import { ArrowLeft, Check, PartyPopper, RotateCcw, Swords, Trophy, Users, Zap } from "lucide-react";
import { ReactNode, useState } from "react";
import { Link } from "react-router-dom";

import { errorMessage } from "../api/client";
import { ChallengeInfo, GameResult } from "../api/games";
import { createChallenges, Friend, getFriends } from "../api/social";
import { Alert, NewBadges } from "./ui";

/** Pick friends to send this exact round to. */
function ChallengeFriends({ roundId, score }: { roundId: string; score: number }) {
  const [friends, setFriends] = useState<Friend[] | null>(null);
  const [chosen, setChosen] = useState<Set<string>>(new Set());
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);

  async function open() {
    setIsOpen(true);
    try {
      setFriends((await getFriends()).friends);
    } catch {
      setError("Could not load your friends.");
    }
  }

  async function send() {
    setError(null);
    try {
      await createChallenges(roundId, [...chosen]);
      setSent(true);
    } catch (err) {
      setError(errorMessage(err, "Could not send the challenge."));
    }
  }

  if (sent) {
    return (
      <Alert kind="success">
        Challenge sent. They have 48 hours to beat {score.toLocaleString()}; you will be told how it went.
      </Alert>
    );
  }
  if (!isOpen) {
    return (
      <button type="button" onClick={() => void open()} className="btn-gold w-full">
        <Swords className="h-4 w-4" aria-hidden /> Challenge a friend to beat this
      </button>
    );
  }
  return (
    <div className="rounded-xl border border-ink/10 p-3 text-left">
      <p className="text-sm font-semibold text-ink">Who do you want to challenge?</p>
      {friends === null && !error && <p className="mt-2 text-xs text-ink/50">Loading friends...</p>}
      {friends?.length === 0 && (
        <p className="mt-2 text-sm text-ink/60">
          No friends yet.{" "}
          <Link to="/friends?tab=friends" className="font-semibold text-gold-dark">
            Add some by username
          </Link>
          .
        </p>
      )}
      <ul className="mt-2 space-y-1">
        {friends?.map((friend) => {
          const isChosen = chosen.has(friend.id);
          return (
            <li key={friend.id}>
              <button
                type="button"
                role="checkbox"
                aria-checked={isChosen}
                onClick={() =>
                  setChosen((prev) => {
                    const next = new Set(prev);
                    if (next.has(friend.id)) next.delete(friend.id);
                    else next.add(friend.id);
                    return next;
                  })
                }
                className={[
                  "flex w-full items-center gap-2 rounded-lg border px-3 py-2 text-sm transition",
                  isChosen ? "border-gold bg-gold/10" : "border-ink/10 hover:bg-ink/5",
                ].join(" ")}
              >
                <span
                  className={[
                    "flex h-4 w-4 items-center justify-center rounded border",
                    isChosen ? "border-gold bg-gold text-navy-dark" : "border-ink/30",
                  ].join(" ")}
                >
                  {isChosen && <Check className="h-3 w-3" aria-hidden />}
                </span>
                <span className="font-medium text-ink">{friend.full_name}</span>
                {friend.username && <span className="text-xs text-ink/50">@{friend.username}</span>}
              </button>
            </li>
          );
        })}
      </ul>
      {error && (
        <div className="mt-2">
          <Alert>{error}</Alert>
        </div>
      )}
      {!!friends?.length && (
        <button type="button" onClick={() => void send()} disabled={chosen.size === 0} className="btn-primary mt-3 w-full">
          <Swords className="h-4 w-4" aria-hidden /> Send challenge{chosen.size > 1 ? "s" : ""}
        </button>
      )}
    </div>
  );
}

/** End-of-round screen shared by every game. */
export default function GameResultCard({
  result,
  backTo,
  onPlayAgain,
  detail,
  challenge,
}: {
  result: GameResult;
  backTo: string;
  onPlayAgain: () => void;
  detail?: ReactNode;
  /** Set when this round was a friend's challenge. */
  challenge?: ChallengeInfo | null;
}) {
  const verdict = challenge
    ? result.score > challenge.challenger_score
      ? "You won!"
      : result.score < challenge.challenger_score
        ? `${challenge.challenger_name} wins this one`
        : "It's a draw"
    : result.is_personal_best
      ? "New personal best!"
      : "Round complete";
  const celebrate = challenge ? result.score >= challenge.challenger_score : result.is_personal_best;

  return (
    <div className="mx-auto max-w-md animate-pop">
      <div className="card overflow-hidden text-center">
        <div className="bg-gradient-to-br from-navy to-navy-light px-6 pb-6 pt-8 text-white">
          <span className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-gold/20 text-gold">
            {celebrate ? <PartyPopper className="h-8 w-8" aria-hidden /> : <Trophy className="h-8 w-8" aria-hidden />}
          </span>
          <p className="mt-3 text-sm font-semibold uppercase tracking-wide text-gold">{verdict}</p>
          <p className="mt-1 text-5xl font-extrabold tracking-tight">{result.score.toLocaleString()}</p>
          <p className="mt-1 text-sm text-white/60">
            {challenge
              ? `${challenge.challenger_name} scored ${challenge.challenger_score.toLocaleString()}`
              : `Best: ${result.personal_best.toLocaleString()}`}
          </p>
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
          {!challenge && result.round_id && <ChallengeFriends roundId={result.round_id} score={result.score} />}
          <div className="flex gap-2">
            <Link to={backTo} className="btn-secondary flex-1">
              {challenge ? <Users className="h-4 w-4" aria-hidden /> : <ArrowLeft className="h-4 w-4" aria-hidden />}
              {challenge ? "Challenges" : "Arcade"}
            </Link>
            {!challenge && (
              <button type="button" onClick={onPlayAgain} className="btn-primary flex-1">
                <RotateCcw className="h-4 w-4" aria-hidden /> Play again
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
