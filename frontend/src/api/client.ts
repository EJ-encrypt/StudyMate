import axios from "axios";

import { isNetworkError, OFFLINE_MESSAGE } from "../lib/network";
import { accessToken } from "../lib/supabase";
import { toast } from "../lib/toast";

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

// Whatever a page shows for its own failure, a lost connection is also said
// plainly, once, rather than as a vague "could not load".
let lastOfflineToast = 0;
apiClient.interceptors.response.use(undefined, (error) => {
  if (isNetworkError(error) && Date.now() - lastOfflineToast > 10_000) {
    lastOfflineToast = Date.now();
    toast(OFFLINE_MESSAGE, { kind: "error", duration: 6000 });
  }
  return Promise.reject(error);
});

/** The server's explanation for a failed request, when it gave one; "you're offline" when nothing came back. */
export function errorMessage(error: unknown, fallback: string): string {
  if (isNetworkError(error)) return OFFLINE_MESSAGE;
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
  }
  return fallback;
}
