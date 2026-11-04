import { apiClient } from "./client";
import { NewBadge } from "./assessments";

export type GameName = "beat_the_clock" | "concept_match";

export interface ClockQuestion {
  item_id: string;
  kind: "mcq" | "fill_blank";
  question: string;
  /** Empty when the answer has to be typed. */
  options: string[];
  answer: string;
  explanation: string;
}

export interface ClockRound {
  course_id: string;
  seconds_per_question: number;
  questions: ClockQuestion[];
  personal_best: number | null;
}

export interface MatchPair {
  concept_id: string;
  name: string;
  clue: string;
}

export type MatchVariety = "fresh" | "mixing" | "repeating";

export interface MatchRound {
  course_id: string;
  /** Set when the round came from one file rather than the whole course. */
  document_id: string | null;
  pairs: MatchPair[];
  personal_best: number | null;
  /** Concepts in the material the round was drawn from. */
  pool_size: number;
  /** Pairs never matched before in a finished round. */
  fresh_in_round: number;
  /** Further rounds possible from concepts never matched. */
  fresh_rounds_left: number;
  rounds_played: number;
  variety: MatchVariety;
}

export interface GameResult {
  game: GameName;
  score: number;
  correct: number;
  total: number;
  xp_awarded: number;
  personal_best: number;
  is_personal_best: boolean;
  new_badges: NewBadge[];
  answers: { item_id: string; correct: boolean; points: number }[];
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

export async function startBeatTheClock(courseId: string): Promise<ClockRound> {
  const { data } = await apiClient.get<ClockRound>(`/games/${courseId}/beat-the-clock`);
  return data;
}

export async function submitBeatTheClock(
  courseId: string,
  answers: { item_id: string; response: string; time_ms: number }[],
): Promise<GameResult> {
  const { data } = await apiClient.post<GameResult>("/games/beat-the-clock", {
    course_id: courseId,
    answers,
  });
  return data;
}

export async function startConceptMatch(courseId: string, documentId?: string | null): Promise<MatchRound> {
  const { data } = await apiClient.get<MatchRound>(`/games/${courseId}/concept-match`, {
    params: documentId ? { document_id: documentId } : undefined,
  });
  return data;
}

export async function submitConceptMatch(
  courseId: string,
  conceptIds: string[],
  mistakes: number,
  durationMs: number,
): Promise<GameResult> {
  const { data } = await apiClient.post<GameResult>("/games/concept-match", {
    course_id: courseId,
    concept_ids: conceptIds,
    mistakes,
    duration_ms: durationMs,
  });
  return data;
}
