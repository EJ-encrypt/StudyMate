import { apiClient } from "./client";
import { NewBadge } from "./assessments";

export type GameName = "beat_the_clock" | "concept_match" | "true_false" | "odd_one_out" | "three_strikes";
/** How each game appears in URLs: /play/:courseId/:path and /games/:courseId/:slug. */
export type GameSlug = "beat-the-clock" | "concept-match" | "true-false" | "odd-one-out" | "three-strikes";

/** Page path under /play/:courseId/ for each game. */
export const GAME_PATHS: Record<GameName, string> = {
  beat_the_clock: "clock",
  concept_match: "match",
  true_false: "blitz",
  odd_one_out: "odd",
  three_strikes: "strikes",
};

export interface ChallengeInfo {
  id: string;
  challenger_name: string;
  challenger_score: number;
}

/** Fields every dealt round has; each game adds its own content. */
export interface RoundBase {
  round_id: string;
  game: GameName;
  course_id: string;
  /** "MATH 223 · Calculus II". */
  title: string;
  personal_best: number | null;
  /** Set when playing a friend's challenge. */
  challenge: ChallengeInfo | null;
}

export interface ClockQuestion {
  item_id: string;
  kind: "mcq" | "fill_blank";
  question: string;
  /** Empty when the answer has to be typed. */
  options: string[];
  answer: string;
  explanation: string;
}

export interface ClockRound extends RoundBase {
  seconds_per_question: number;
  questions: ClockQuestion[];
}

export interface StrikesRound extends RoundBase {
  questions: ClockQuestion[];
  strikes: number;
}

export interface MatchPair {
  concept_id: string;
  name: string;
  clue: string;
}

export type MatchVariety = "fresh" | "mixing" | "repeating";

export interface MatchRound extends RoundBase {
  /** Set when the round came from one file rather than the whole course. */
  document_id: string | null;
  pairs: MatchPair[];
  /** Concepts in the material the round was drawn from. */
  pool_size: number;
  /** Pairs never matched before in a finished round. */
  fresh_in_round: number;
  /** Further rounds possible from concepts never matched. */
  fresh_rounds_left: number;
  rounds_played: number;
  variety: MatchVariety;
}

export interface Statement {
  key: string;
  subject: string;
  claim: string;
  is_true: boolean;
  explanation: string;
}

export interface BlitzRound extends RoundBase {
  seconds: number;
  statements: Statement[];
}

export interface OddOption {
  concept_id: string;
  name: string;
  summary: string;
}

export interface OddPuzzle {
  options: OddOption[];
  odd_id: string;
  /** The concept the three that belong are grouped around. */
  theme: string;
}

export interface OddRound extends RoundBase {
  puzzles: OddPuzzle[];
}

export interface RoundAnswer {
  /** Item id, statement key or puzzle position. */
  key: string;
  response: string;
  time_ms: number;
}

export interface RoundSubmission {
  answers?: RoundAnswer[];
  /** Concept Match only. */
  mistakes?: number;
  duration_ms?: number;
}

export interface GameResult {
  game: GameName;
  /** Present for your own rounds, so a friend can be challenged to the same one. */
  round_id: string | null;
  score: number;
  correct: number;
  total: number;
  xp_awarded: number;
  personal_best: number;
  is_personal_best: boolean;
  new_badges: NewBadge[];
  answers: { key: string; correct: boolean; points: number }[];
}

export interface GameStats {
  game: GameName;
  plays: number;
  best: number | null;
  last_played_at: string | null;
}

export interface CourseGameStats {
  course_id: string;
  games: GameStats[];
  clock_questions_available: number;
  concepts_available: number;
  /** Whole-course Concept Match rounds still possible without repeats. */
  match_fresh_rounds: number;
}

export async function getGameStats(courseId: string): Promise<CourseGameStats> {
  const { data } = await apiClient.get<CourseGameStats>(`/games/${courseId}/stats`);
  return data;
}

export async function startRound<T extends RoundBase>(
  courseId: string,
  slug: GameSlug,
  documentId?: string | null,
): Promise<T> {
  const { data } = await apiClient.get<T>(`/games/${courseId}/${slug}`, {
    params: documentId ? { document_id: documentId } : undefined,
  });
  return data;
}

export async function submitRound(roundId: string, submission: RoundSubmission): Promise<GameResult> {
  const { data } = await apiClient.post<GameResult>(`/games/rounds/${roundId}/submit`, submission);
  return data;
}

export async function startChallengeRound<T extends RoundBase>(challengeId: string): Promise<T> {
  const { data } = await apiClient.get<T>(`/challenges/${challengeId}/round`);
  return data;
}

export async function submitChallenge(challengeId: string, submission: RoundSubmission): Promise<GameResult> {
  const { data } = await apiClient.post<GameResult>(`/challenges/${challengeId}/submit`, submission);
  return data;
}
