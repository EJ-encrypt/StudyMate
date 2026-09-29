import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import {
  CoachSummary,
  ConceptProgress,
  getCoachSummary,
  STATUS_LABELS,
  STATUS_STYLES,
} from "../api/coach";
import CourseSelect from "../components/CourseSelect";
import PageHeader from "../components/PageHeader";

function StatusBadge({ concept }: { concept: ConceptProgress }) {
  return (
    <span className={`rounded px-2 py-0.5 text-xs font-semibold ${STATUS_STYLES[concept.status]}`}>
      {STATUS_LABELS[concept.status]}
    </span>
  );
}

function MasteryBar({ score }: { score: number | null }) {
  if (score === null) {
    return <div className="h-2 w-full rounded bg-navy/10" />;
  }
  const percent = Math.round(score * 100);
  const colour = score < 0.5 ? "bg-red-500" : score < 0.8 ? "bg-gold" : "bg-green-600";
  return (
    <div className="h-2 w-full rounded bg-navy/10">
      <div className={`h-2 rounded ${colour}`} style={{ width: `${percent}%` }} />
    </div>
  );
}

export default function Coach() {
  const [courseId, setCourseId] = useState<string | null>(null);
  const [summary, setSummary] = useState<CoachSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!courseId) return;
    getCoachSummary(courseId)
      .then((data) => {
        setSummary(data);
        setError(null);
      })
      .catch(() => setError("Could not load your progress for this course."));
  }, [courseId]);

  return (
    <>
      <PageHeader
        title="Coach"
        subtitle="How well you know each topic, from the questions you have answered."
      />

      <div className="mb-4">
        <CourseSelect selectedCourseId={courseId} onSelect={setCourseId} />
      </div>

      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}

      {summary && summary.concept_count === 0 && (
        <p className="mt-8 text-navy/70">
          No concepts yet for this course.{" "}
          <Link to="/courses" className="font-semibold text-gold-dark">
            Add material
          </Link>{" "}
          to get started.
        </p>
      )}

      {summary && summary.concept_count > 0 && (
        <>
          <section className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {[
              ["Strong", summary.strong],
              ["Developing", summary.developing],
              ["Needs work", summary.weak],
              ["Not practised", summary.unpractised],
            ].map(([label, value]) => (
              <div key={label as string} className="rounded border border-navy/15 bg-white p-2.5 text-center">
                <p className="text-xl font-bold text-navy">{value as number}</p>
                <p className="text-sm text-navy/60">{label as string}</p>
              </div>
            ))}
          </section>

          {summary.overall_mastery !== null && (
            <p className="mt-4 text-sm text-navy/70">
              Overall mastery across practised concepts:{" "}
              <span className="font-semibold text-navy">
                {Math.round(summary.overall_mastery * 100)}%
              </span>
            </p>
          )}

          {summary.recommendations.length > 0 && (
            <section className="mt-4 rounded border border-gold bg-gold/10 p-3">
              <h2 className="font-semibold text-navy">Revise these next</h2>
              <ol className="mt-3 flex list-decimal flex-col gap-3 pl-5">
                {summary.recommendations.map((concept) => (
                  <li key={concept.concept_id}>
                    <Link
                      to={`/coach/concept/${concept.concept_id}`}
                      className="group block rounded px-1 py-0.5 hover:bg-white/60"
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-semibold text-navy group-hover:underline">
                          {concept.name}
                        </span>
                        <StatusBadge concept={concept} />
                      </div>
                      <p className="text-sm text-navy/70">{concept.summary}</p>
                    </Link>
                  </li>
                ))}
              </ol>
              <p className="mt-4 text-sm text-navy/70">
                Generate a cumulative quiz from{" "}
                <Link to="/materials" className="font-semibold text-gold-dark">
                  Materials
                </Link>{" "}
                to practise these.
              </p>
            </section>
          )}

          <section className="mt-5">
            <h2 className="font-semibold text-navy">All concepts</h2>
            <ul className="mt-3 flex flex-col gap-4">
              {summary.concepts.map((concept) => (
                <li key={concept.concept_id}>
                  <Link
                    to={`/coach/concept/${concept.concept_id}`}
                    className="flex flex-wrap items-center justify-between gap-2 hover:underline"
                  >
                    <span className="font-semibold text-navy">{concept.name}</span>
                    <div className="flex items-center gap-2">
                      {concept.attempts > 0 && (
                        <span className="text-xs text-navy/60">
                          {concept.correct}/{concept.attempts} correct
                        </span>
                      )}
                      <StatusBadge concept={concept} />
                    </div>
                  </Link>
                  <div className="mt-2">
                    <MasteryBar score={concept.score} />
                  </div>
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </>
  );
}
