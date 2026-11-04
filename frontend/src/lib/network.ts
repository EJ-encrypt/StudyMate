import axios from "axios";
import { useEffect, useState } from "react";

export const OFFLINE_MESSAGE =
  "You're not connected to the internet. Check your Wi-Fi or mobile data, then try again.";

/** Whether the device has a connection; updates as it comes and goes. */
export function useOnline(): boolean {
  const [online, setOnline] = useState(() => (typeof navigator === "undefined" ? true : navigator.onLine));
  useEffect(() => {
    const up = () => setOnline(true);
    const down = () => setOnline(false);
    window.addEventListener("online", up);
    window.addEventListener("offline", down);
    return () => {
      window.removeEventListener("online", up);
      window.removeEventListener("offline", down);
    };
  }, []);
  return online;
}

/**
 * True when a request failed because nothing came back at all: no
 * connection, or it dropped mid-way. Browsers word it differently ("Failed
 * to fetch" in Chrome, "Load failed" on iPhone, "NetworkError" in Firefox).
 */
export function isNetworkError(error: unknown): boolean {
  if (typeof navigator !== "undefined" && !navigator.onLine) return true;
  if (axios.isAxiosError(error)) return !error.response && error.code !== "ERR_CANCELED";
  const message = error instanceof Error ? error.message : typeof error === "string" ? error : "";
  return /failed to fetch|load failed|networkerror|network request failed|network error/i.test(message);
}
