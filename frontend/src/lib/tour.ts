import { useEffect, useState } from "react";

/**
 * Whether the guided tour is running. It starts by itself for a new student
 * once onboarding is done (components/Tour.tsx), and from Settings, App tour.
 */
let active = false;
const listeners = new Set<(value: boolean) => void>();

function set(value: boolean) {
  active = value;
  listeners.forEach((listener) => listener(active));
}

export const startTour = () => set(true);
export const stopTour = () => set(false);

export function useTourActive(): boolean {
  const [value, setValue] = useState(active);
  useEffect(() => {
    listeners.add(setValue);
    setValue(active);
    return () => {
      listeners.delete(setValue);
    };
  }, []);
  return value;
}
