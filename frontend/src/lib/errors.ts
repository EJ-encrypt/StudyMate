/**
 * Crash reports from students' browsers (Sentry), so a broken page is seen
 * and fixed without anyone having to describe it. Only loaded when the build
 * has a DSN, so it costs nothing otherwise. No personal data: no email, no
 * page content, no recordings.
 */
export async function startErrorReporting(): Promise<void> {
  const dsn = import.meta.env.VITE_SENTRY_DSN as string | undefined;
  if (!dsn) return;
  const Sentry = await import("@sentry/browser");
  Sentry.init({
    dsn,
    environment: import.meta.env.MODE,
    // Errors only; no performance tracing or session replay.
    tracesSampleRate: 0,
  });
}
