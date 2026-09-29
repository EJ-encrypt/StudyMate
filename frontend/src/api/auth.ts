import { apiClient } from "./client";

export interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

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
}

export interface OnboardingDetails {
  school: string;
  programme: string;
  level: number;
  semester: number;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export async function register(payload: RegisterPayload): Promise<UserProfile> {
  const { data } = await apiClient.post<UserProfile>("/auth/register", payload);
  return data;
}

export async function login(payload: LoginPayload): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>("/auth/login", payload);
  return data;
}

export async function fetchCurrentUser(): Promise<UserProfile> {
  const { data } = await apiClient.get<UserProfile>("/auth/me");
  return data;
}

export async function completeOnboarding(details: OnboardingDetails): Promise<UserProfile> {
  const { data } = await apiClient.put<UserProfile>("/auth/me/onboarding", details);
  return data;
}
