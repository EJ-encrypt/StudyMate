import { Check, Crown, Medal, Swords, Trophy, UserMinus, UserPlus, Users, X } from "lucide-react";
import { FormEvent, ReactNode, useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { updatePreferences } from "../api/auth";
import { errorMessage } from "../api/client";
import { GAME_PATHS } from "../api/games";
import {
  acceptFriendRequest,
  Challenge,
  declineFriendRequest,
  FriendsOverview,
  getFriends,
  getLeaderboard,
  Leaderboard,
  LeaderboardPeriod,
  LeaderboardScope,
  listChallenges,
  removeFriend,
  sendFriendRequest,
} from "../api/social";
import PageHeader from "../components/PageHeader";
import StudentActions from "../components/StudentActions";
import { Alert, EmptyState, ListSkeleton } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { undoable } from "../lib/toast";

type Tab = "leaderboard" | "friends" | "challenges";

function Segmented<T extends string>({
  value,
  options,
  onChange,
  label,
}: {
  value: T;
  options: [T, string][];
  onChange: (value: T) => void;
  label: string;
}) {
  return (
    <div role="tablist" aria-label={label} className="inline-flex rounded-lg bg-ink/5 p-1">
      {options.map(([option, text]) => (
        <button
          key={option}
          type="button"
          role="tab"
          aria-selected={value === option}
          onClick={() => onChange(option)}
          className={[
            "rounded-md px-3 py-1.5 text-sm font-semibold transition",
            value === option ? "bg-surface text-ink shadow-sm" : "text-ink/60 hover:text-ink",
          ].join(" ")}
        >
          {text}
        </button>
      ))}
    </div>
  );
}

function RankBadge({ rank }: { rank: number }) {
  const styles = ["bg-gold text-navy-dark", "bg-slate-300 text-slate-800", "bg-amber-700 text-white"];
  if (rank <= 3) {
    const Icon = rank === 1 ? Crown : Medal;
    return (
      <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${styles[rank - 1]}`}>
        <Icon className="h-4 w-4" aria-hidden />
        <span className="sr-only">{rank}</span>
      </span>
    );
  }
  return (
    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-ink/5 text-sm font-bold text-ink/60">
      {rank}
    </span>
  );
}

function LeaderboardTab() {
  const { user, refresh } = useAuth();
  const [scope, setScope] = useState<LeaderboardScope>("friends");
  const [period, setPeriod] = useState<LeaderboardPeriod>("week");
  const [board, setBoard] = useState<Leaderboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setBoard(null);
    getLeaderboard(scope, period)
      .then(setBoard)
      .catch(() => setError("Could not load the leaderboard."));
  }, [scope, period]);

  useEffect(load, [load]);

  async function join(value: boolean) {
    await updatePreferences({ public_leaderboard: value });
    await refresh();
    load();
  }

  return (
    <>
      <div className="mb-4 flex flex-wrap gap-2">
        <Segmented
          label="Who"
          value={scope}
          onChange={setScope}
          options={[
            ["friends", "Friends"],
            ["programme", "My programme"],
          ]}
        />
        <Segmented
          label="When"
          value={period}
          onChange={setPeriod}
          options={[
            ["week", "This week"],
            ["all", "All time"],
          ]}
        />
      </div>

      {error && <Alert>{error}</Alert>}
      {!board && !error && <ListSkeleton rows={4} />}

      {board && scope === "programme" && (
        <div className="card mb-4 flex flex-wrap items-center justify-between gap-3 p-4">
          <div className="min-w-0">
            <p className="text-sm font-semibold text-ink">{board.programme ?? "No programme set"}</p>
            <p className="text-xs text-ink/55">
              {board.joined
                ? `You appear as ${user?.username ? `@${user.username}` : "your first name and initial"}. Only XP is shown.`
                : "Join to compare XP with everyone on your programme. Only your username and XP are shown."}
            </p>
          </div>
          <button
            type="button"
            onClick={() => void join(!board.joined)}
            className={board.joined ? "btn-ghost text-xs" : "btn-primary"}
          >
            {board.joined ? "Leave this board" : "Join the board"}
          </button>
        </div>
      )}

      {board && board.standings.length <= 1 && scope === "friends" && (
        <p className="mb-3 text-sm text-ink/60">Add friends to see how you compare. Weekly scores reset every Monday.</p>
      )}

      {board && board.standings.length > 0 && (
        <ol className="card divide-y divide-ink/5">
          {board.standings.map((standing) => (
            <li
              key={standing.student_id}
              className={["flex items-center gap-3 px-4 py-3", standing.is_me ? "bg-gold/10" : ""].join(" ")}
            >
              <RankBadge rank={standing.rank} />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold text-ink">
                  {standing.name}
                  {standing.is_me && <span className="font-normal text-ink/50"> (you)</span>}
                </p>
                {scope === "friends" && standing.username && (
                  <p className="truncate text-xs text-ink/50">@{standing.username}</p>
                )}
              </div>
              <span className="text-sm font-bold tabular-nums text-ink">{standing.xp.toLocaleString()} XP</span>
              {!standing.is_me && <StudentActions studentId={standing.student_id} name={standing.name} onChanged={load} />}
            </li>
          ))}
        </ol>
      )}
    </>
  );
}

function FriendsTab() {
  const { user } = useAuth();
  const [overview, setOverview] = useState<FriendsOverview | null>(null);
  const [username, setUsername] = useState("");
  const [message, setMessage] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  // Friends just removed, hidden while their Undo is on screen.
  const [leaving, setLeaving] = useState<string[]>([]);

  const load = useCallback(() => {
    getFriends()
      .then(setOverview)
      .catch(() => setMessage({ kind: "error", text: "Could not load your friends." }));
  }, []);

  useEffect(load, [load]);

  async function add(event: FormEvent) {
    event.preventDefault();
    setMessage(null);
    try {
      await sendFriendRequest(username.trim());
      setUsername("");
      setMessage({ kind: "success", text: "Request sent." });
      load();
    } catch (err) {
      setMessage({ kind: "error", text: errorMessage(err, "Could not send that request.") });
    }
  }

  async function act(action: () => Promise<void>) {
    try {
      await action();
    } finally {
      load();
    }
  }

  return (
    <>
      <form onSubmit={add} className="card mb-4 p-4">
        <label className="block">
          <span className="label">Add a friend by username</span>
          <div className="mt-1 flex gap-2">
            <div className="relative flex-1">
              <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-sm text-ink/40">@</span>
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value.replace(/^@/, ""))}
                placeholder="their_username"
                autoCapitalize="none"
                autoCorrect="off"
                className="input pl-7"
              />
            </div>
            <button type="submit" disabled={!username.trim()} className="btn-primary">
              <UserPlus className="h-4 w-4" aria-hidden /> Add
            </button>
          </div>
        </label>
        <p className="mt-2 text-xs text-ink/55">
          {user?.username ? (
            <>
              Your username is <span className="font-semibold text-ink">@{user.username}</span>. Share it so friends can
              add you.
            </>
          ) : (
            <>
              Set a username in <Link to="/settings?section=profile" className="font-semibold text-gold-dark">Settings</Link> so friends
              can find you.
            </>
          )}
        </p>
        {message && (
          <div className="mt-3">
            <Alert kind={message.kind}>{message.text}</Alert>
          </div>
        )}
      </form>

      {!overview && <ListSkeleton rows={4} />}

      {overview && overview.incoming.length > 0 && (
        <section className="mb-4">
          <h2 className="section-title">Requests for you</h2>
          <ul className="card divide-y divide-ink/5">
            {overview.incoming.map(({ request_id, user: other }) => (
              <li key={request_id} className="flex items-center gap-3 px-4 py-3">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-ink">{other.full_name}</p>
                  <p className="truncate text-xs text-ink/50">
                    {other.username && `@${other.username}`}
                    {other.programme && ` · ${other.programme}`}
                  </p>
                </div>
                <button type="button" onClick={() => void act(() => acceptFriendRequest(request_id))} className="btn-primary px-3 py-1.5 text-xs">
                  <Check className="h-3.5 w-3.5" aria-hidden /> Accept
                </button>
                <button
                  type="button"
                  onClick={() => void act(() => declineFriendRequest(request_id))}
                  aria-label={`Decline ${other.full_name}`}
                  className="btn-ghost p-1.5"
                >
                  <X className="h-4 w-4" aria-hidden />
                </button>
                <StudentActions studentId={other.id} name={other.full_name} onChanged={load} />
              </li>
            ))}
          </ul>
        </section>
      )}

      {overview && (
        <section className="mb-4">
          <h2 className="section-title">Friends · {overview.friends.length - leaving.length}</h2>
          {overview.friends.length - leaving.length === 0 ? (
            <EmptyState icon={Users} title="No friends yet">
              Add classmates by their username to compare progress and challenge them in the Arcade.
            </EmptyState>
          ) : (
            <ul className="card divide-y divide-ink/5">
              {overview.friends.filter((friend) => !leaving.includes(friend.id)).map((friend) => (
                <li key={friend.id} className="flex items-center gap-3 px-4 py-3">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-ink">{friend.full_name}</p>
                    <p className="truncate text-xs text-ink/50">
                      {friend.username && `@${friend.username}`}
                      {friend.programme && ` · ${friend.programme}`}
                    </p>
                  </div>
                  <span className="text-xs font-semibold text-ink/60">{friend.xp.toLocaleString()} XP</span>
                  <button
                    type="button"
                    onClick={() =>
                      undoable({
                        text: `${friend.full_name} removed from your friends.`,
                        hide: () => setLeaving((ids) => [...ids, friend.id]),
                        restore: () => setLeaving((ids) => ids.filter((id) => id !== friend.id)),
                        commit: async () => {
                          await removeFriend(friend.id);
                          setLeaving((ids) => ids.filter((id) => id !== friend.id));
                          load();
                        },
                      })
                    }
                    aria-label={`Remove ${friend.full_name}`}
                    className="btn-ghost p-1.5 text-ink/40"
                  >
                    <UserMinus className="h-4 w-4" aria-hidden />
                  </button>
                  <StudentActions studentId={friend.id} name={friend.full_name} onChanged={load} />
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {overview && overview.outgoing.length > 0 && (
        <section>
          <h2 className="section-title">Waiting for them to accept</h2>
          <ul className="card divide-y divide-ink/5">
            {overview.outgoing.map(({ request_id, user: other }) => (
              <li key={request_id} className="flex items-center gap-3 px-4 py-3">
                <p className="min-w-0 flex-1 truncate text-sm text-ink">
                  {other.full_name} {other.username && <span className="text-ink/50">@{other.username}</span>}
                </p>
                <button type="button" onClick={() => void act(() => removeFriend(other.id))} className="btn-ghost text-xs">
                  Cancel
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}

function hoursLeft(iso: string): string {
  const hours = Math.max(0, Math.round((new Date(iso).getTime() - Date.now()) / 3_600_000));
  return hours >= 1 ? `${hours}h left` : "under an hour left";
}

function ChallengesTab() {
  const [challenges, setChallenges] = useState<Challenge[] | null>(null);

  useEffect(() => {
    listChallenges()
      .then(setChallenges)
      .catch(() => setChallenges([]));
  }, []);

  if (!challenges) return <ListSkeleton rows={4} />;
  if (challenges.length === 0) {
    return (
      <EmptyState
        icon={Swords}
        title="No challenges yet"
        action={
          <Link to="/play" className="btn-primary">
            Go to the Arcade
          </Link>
        }
      >
        Finish any Arcade round, then tap "Challenge a friend" to send them the exact same round.
      </EmptyState>
    );
  }

  const waiting = challenges.filter((c) => c.direction === "received" && c.status === "open");
  const rest = challenges.filter((c) => !(c.direction === "received" && c.status === "open"));

  const row = (challenge: Challenge, action?: ReactNode) => (
    <li key={challenge.id} className="flex items-center gap-3 px-4 py-3">
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-ink">
          {challenge.game_name}
          <span className="font-normal text-ink/55">
            {" "}
            {challenge.direction === "sent" ? "to" : "from"} {challenge.other?.full_name ?? "a friend"}
          </span>
        </p>
        <p className="truncate text-xs text-ink/50">{challenge.title}</p>
      </div>
      {action ?? (
        <div className="text-right text-xs">
          {challenge.status === "completed" ? (
            <>
              <p
                className={[
                  "font-bold",
                  challenge.outcome === "won" ? "text-green-700" : challenge.outcome === "lost" ? "text-red-600" : "text-ink",
                ].join(" ")}
              >
                {challenge.outcome === "won" ? "Won" : challenge.outcome === "lost" ? "Lost" : "Draw"}
              </p>
              <p className="tabular-nums text-ink/55">
                {challenge.my_score?.toLocaleString()} – {challenge.their_score?.toLocaleString()}
              </p>
            </>
          ) : challenge.status === "expired" ? (
            <p className="text-ink/45">Expired</p>
          ) : (
            <p className="text-ink/55">Waiting · {hoursLeft(challenge.expires_at)}</p>
          )}
        </div>
      )}
    </li>
  );

  return (
    <>
      {waiting.length > 0 && (
        <section className="mb-4">
          <h2 className="section-title">Your move</h2>
          <ul className="card divide-y divide-ink/5 border-gold">
            {waiting.map((challenge) =>
              row(
                challenge,
                <div className="flex shrink-0 flex-col items-end gap-1">
                  <Link
                    to={`/play/challenge/${GAME_PATHS[challenge.game]}?challenge=${challenge.id}`}
                    className="btn-gold px-3 py-1.5 text-xs"
                  >
                    <Swords className="h-3.5 w-3.5" aria-hidden /> Beat {challenge.their_score?.toLocaleString()}
                  </Link>
                  <span className="text-[11px] text-ink/45">{hoursLeft(challenge.expires_at)}</span>
                </div>,
              ),
            )}
          </ul>
        </section>
      )}
      {rest.length > 0 && (
        <section>
          <h2 className="section-title">History</h2>
          <ul className="card divide-y divide-ink/5">{rest.map((challenge) => row(challenge))}</ul>
        </section>
      )}
    </>
  );
}

export default function Friends() {
  const [params, setParams] = useSearchParams();
  const tab = (["leaderboard", "friends", "challenges"].includes(params.get("tab") ?? "") ? params.get("tab") : "leaderboard") as Tab;

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader icon={Trophy} title="Leaderboard" subtitle="Leaderboards, friends and challenges." />
      <div className="mb-5">
        <Segmented
          label="Section"
          value={tab}
          onChange={(value) => setParams({ tab: value }, { replace: true })}
          options={[
            ["leaderboard", "Leaderboard"],
            ["friends", "Friends"],
            ["challenges", "Challenges"],
          ]}
        />
      </div>
      {tab === "leaderboard" && <LeaderboardTab />}
      {tab === "friends" && <FriendsTab />}
      {tab === "challenges" && <ChallengesTab />}
    </div>
  );
}
