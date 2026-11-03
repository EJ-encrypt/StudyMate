import { apiClient } from "./client";

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  role: "student" | "lecturer";
  /** Null until onboarding is completed, which is how the app detects it. */
  school: string | null;
  programme: string | null;
  level: number | null;
  semester: number | null;
  timezone: string;
  notify_push: boolean;
  notify_email: boolean;
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
