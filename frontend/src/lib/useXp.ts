import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";

import { getProgress } from "../api/profile";

/**
 * The student's XP for the navigation, shared by the sidebar and the phone
 * header so they make one request between them. Re-read when the student
 * moves to another page (a finished game or quiz has usually just added
 * some), but not more often than every few seconds.
 */
const MIN_GAP_MS = 5000;

let xp: number | null = null;
let fetchedAt = 0;
let inFlight: Promise<void> | null = null;
const listeners = new Set<(value: number | null) => void>();

function refresh(force = false) {
  if (inFlight || (!force && Date.now() - fetchedAt < MIN_GAP_MS)) return;
  fetchedAt = Date.now();
  inFlight = getProgress()
    .then((progress) => {
      xp = progress.xp;
      listeners.forEach((listener) => listener(xp));
    })
    .catch(() => undefined)
    .finally(() => {
      inFlight = null;
    });
}

export function useXp(enabled = true): number | null {
  const { pathname } = useLocation();
  const [value, setValue] = useState(xp);

  useEffect(() => {
    listeners.add(setValue);
    return () => {
      listeners.delete(setValue);
    };
  }, []);

  useEffect(() => {
    if (enabled) refresh();
  }, [enabled, pathname]);

  return value;
}

/** Shown as "1,240 XP"; compact on phones past ten thousand ("12.4k XP"). */
export function formatXp(value: number, compact = false): string {
  if (compact && value >= 10_000) return `${(value / 1000).toFixed(value >= 100_000 ? 0 : 1)}k XP`;
  return `${value.toLocaleString()} XP`;
}
