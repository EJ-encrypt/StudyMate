import { apiClient } from "./client";

let running = false;
let again = false;

/**
 * Ask the server to process this student's queued uploads and quizzes now.
 *
 * Fire-and-forget: the page already polls for status, and if this request is
 * cut short (the tab closes, the function times out) the scheduler's sweep
 * picks the work up within a minute. A call made while a run is in flight
 * queues exactly one more run after it, in case the first had already found
 * the queue empty before the new job arrived.
 */
export function runMyJobs(): void {
  if (running) {
    again = true;
    return;
  }
  running = true;
  apiClient
    .post("/jobs/run", undefined, { timeout: 310_000 })
    .catch(() => undefined)
    .finally(() => {
      running = false;
      if (again) {
        again = false;
        runMyJobs();
      }
    });
}
