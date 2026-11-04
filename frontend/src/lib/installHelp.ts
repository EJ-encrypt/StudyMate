import { useEffect, useState } from "react";

/**
 * The sheet that explains adding StudyMate to the Home Screen. Opened when
 * someone on an iPhone tries to turn on notifications, which iPhones only
 * allow for web apps added that way.
 */
let open = false;
const listeners = new Set<(value: boolean) => void>();

function set(value: boolean) {
  open = value;
  listeners.forEach((listener) => listener(open));
}

export const showInstallHelp = () => set(true);
export const hideInstallHelp = () => set(false);

export function useInstallHelpOpen(): boolean {
  const [value, setValue] = useState(open);
  useEffect(() => {
    listeners.add(setValue);
    return () => {
      listeners.delete(setValue);
    };
  }, []);
  return value;
}
