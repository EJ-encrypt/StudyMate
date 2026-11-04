import { apiClient } from "./client";

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  username: string | null;
  role: "student" | "lecturer";
  /** Null until onboarding is completed, which is how the app detects it. */
  school: string | null;
  programme: string | null;
  level: number | null;
  semester: number | null;
  timezone: string;
  notify_push: boolean;
  notify_email: boolean;
  /** Whether the first-run walkthrough has been finished or skipped. */
  tutorial_seen: boolean;
}

export interface OnboardingDetails {
  school: string;
  programme: string;
  level: number;
  semester: number;
  timezone?: string;
}

export interface Preferences {
  full_name?: string;
  /** An empty string clears it. */
  username?: string;
  level?: number;
  semester?: number;
  tutorial_seen?: boolean;
  timezone?: string;
  notify_push?: boolean;
  notify_email?: boolean;
}

export function browserTimezone(): string | undefined {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone;
  } catch {
    return undefined;
  }
}

export async function fetchCurrentUser(): Promise<UserProfile> {
  const { data } = await apiClient.get<UserProfile>("/auth/me");
  return data;
}

export async function completeOnboarding(details: OnboardingDetails): Promise<UserProfile> {
  const { data } = await apiClient.put<UserProfile>("/auth/me/onboarding", details);
  return data;
}

export async function updatePreferences(preferences: Preferences): Promise<UserProfile> {
  const { data } = await apiClient.patch<UserProfile>("/auth/me/preferences", preferences);
  return data;
}

/** Deletes the account and everything in it. The caller signs out afterwards. */
export async function deleteAccount(): Promise<void> {
  await apiClient.delete("/auth/me");
}
