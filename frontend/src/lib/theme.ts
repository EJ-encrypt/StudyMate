/**
 * Light, dark, or whatever the device uses. Kept in this browser rather than
 * on the account: someone may well want dark on their phone at night and
 * light on a lab computer.
 *
 * public/theme-init.js applies the saved choice before the page draws, so a dark-mode
 * user never sees a white flash; this module keeps it in sync afterwards.
 */

export type ThemeChoice = "light" | "dark" | "system";

const STORAGE_KEY = "studymate-theme";
const THEME_COLOURS = { light: "#0A1F44", dark: "#070F1F" };

const darkQuery = (): MediaQueryList | null =>
  typeof window !== "undefined" && window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;

export function getThemeChoice(): ThemeChoice {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === "light" || saved === "dark" || saved === "system") return saved;
  } catch {
    // Storage blocked (private mode): fall through to the default.
  }
  return "system";
}

function resolve(choice: ThemeChoice): "light" | "dark" {
  if (choice !== "system") return choice;
  return darkQuery()?.matches ? "dark" : "light";
}

export function applyTheme(choice: ThemeChoice = getThemeChoice()): void {
  const theme = resolve(choice);
  document.documentElement.classList.toggle("dark", theme === "dark");
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", THEME_COLOURS[theme]);
}

export function setThemeChoice(choice: ThemeChoice): void {
  try {
    localStorage.setItem(STORAGE_KEY, choice);
  } catch {
    // Still applied for this visit, just not remembered.
  }
  applyTheme(choice);
}

/** Follow the device when it switches between light and dark, if set to "system". */
export function watchSystemTheme(): () => void {
  const query = darkQuery();
  if (!query) return () => undefined;
  const onChange = () => {
    if (getThemeChoice() === "system") applyTheme("system");
  };
  query.addEventListener("change", onChange);
  return () => query.removeEventListener("change", onChange);
}
