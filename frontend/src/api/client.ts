import axios from "axios";

import { accessToken } from "../lib/supabase";

export const apiClient = axios.create({
  // On Vercel the API is served from /api on the same origin as the page.
  // In development Vite proxies /api to the local backend (vite.config.ts).
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
});

apiClient.interceptors.request.use(async (config) => {
  // Supabase refreshes the token in the background; asking for the session on
  // every request always yields a current one.
  const token = await accessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/** The server's explanation for a failed request, when it gave one. */
export function errorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
  }
  return fallback;
}
