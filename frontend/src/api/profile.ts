import { apiClient } from "./client";

export interface Badge {
  code: string;
  name: string;
  description: string;
  /** Null while the badge is still unearned. */
  earned_at: string | null;
}

export interface ProgressSummary {
  xp: number;
  current_streak: number;
  longest_streak: number;
  last_active_on: string | null;
  documents: number;
  attempts: number;
  badges: Badge[];
  /** Study sessions wanted per day, and how many are done so far today. */
  daily_goal: number;
  done_today: number;
}

export async function getProgress(): Promise<ProgressSummary> {
  const { data } = await apiClient.get<ProgressSummary>("/profile/progress");
  return data;
}
