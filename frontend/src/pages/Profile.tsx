import { useEffect, useState } from "react";

import { getProgress, ProgressSummary } from "../api/profile";
import { useAuth } from "../context/AuthContext";

export default function Profile() {
  const { user } = useAuth();
  const [progress, setProgress] = useState<ProgressSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getProgress()
      .then(setProgress)
      .catch(() => setError("Could not load your progress."));
  }, []);

  const earned = progress?.badges.filter((badge) => badge.earned_at !== null) ?? [];
  const locked = progress?.badges.filter((badge) => badge.earned_at === null) ?? [];

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="text-2xl font-bold text-navy">Profile</h1>

      <dl className="mt-4 grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-navy">
        <dt className="font-semibold">Name</dt>
        <dd>{user?.full_name}</dd>
        <dt className="font-semibold">Email</dt>
        <dd>{user?.email}</dd>
        <dt className="font-semibold">Role</dt>
        <dd className="capitalize">{user?.role}</dd>
      </dl>

      {error && <p className="mt-6 text-sm text-red-600">{error}</p>}

      {progress && (
        <>
          <section className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              ["XP", progress.xp],
              ["Day streak", progress.current_streak],
              ["Best streak", progress.longest_streak],
              ["Quizzes taken", progress.attempts],
            ].map(([label, value]) => (
              <div key={label as string} className="rounded border border-navy/10 p-3 text-center">
                <p className="text-2xl font-bold text-navy">{value as number}</p>
                <p className="text-sm text-navy/60">{label as string}</p>
              </div>
            ))}
          </section>

          <p className="mt-3 text-sm text-navy/60">
            {progress.documents} document{progress.documents === 1 ? "" : "s"} uploaded
            {progress.last_active_on && ` \u00b7 last studied ${progress.last_active_on}`}
          </p>

          <section className="mt-8">
            <h2 className="font-semibold text-navy">
              Badges
              <span className="ml-2 text-sm font-normal text-navy/60">
                {earned.length} of {progress.badges.length}
              </span>
            </h2>

            <ul className="mt-3 flex flex-col gap-2">
              {earned.map((badge) => (
                <li
                  key={badge.code}
                  className="rounded border border-gold bg-gold/10 p-3"
                >
                  <p className="font-semibold text-navy">{badge.name}</p>
                  <p className="text-sm text-navy/70">{badge.description}</p>
                </li>
              ))}
              {locked.map((badge) => (
                <li key={badge.code} className="rounded border border-navy/10 p-3 opacity-60">
                  <p className="font-semibold text-navy">{badge.name}</p>
                  <p className="text-sm text-navy/70">{badge.description}</p>
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </div>
  );
}
