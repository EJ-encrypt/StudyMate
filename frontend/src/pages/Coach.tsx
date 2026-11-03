import { Lightbulb, ListTree, Target } from "lucide-react";
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
import { Alert, EmptyState, StatTile } from "../components/ui";

function StatusBadge({ concept }: { concept: ConceptProgress }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${STATUS_STYLES[concept.status]}`}>
      {STATUS_LABELS[concept.status]}
    </span>
  );
}

function MasteryBar({ score }: { score: number | null }) {
  if (score === null) {
    return <div className="h-2 w-full rounded-full bg-navy/10" />;
  }
  const percent = Math.round(score * 100);
  const colour = score < 0.5 ? "bg-red-500" : score < 0.8 ? "bg-gold" : "bg-green-600";
  return (
    <div className="h-2 w-full rounded-full bg-navy/10">
      <div className={`h-2 rounded-full ${colour} transition-all`} style={{ width: `${percent}%` }} />
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
        icon={Target}
        title="Coach"
        subtitle="How well you know each topic, from the questions you have answered."
      />

      <div className="mb-4">
        <CourseSelect selectedCourseId={courseId} onSelect={setCourseId} />
      </div>

      {error && <Alert>{error}</Alert>}

      {summary && summary.concept_count === 0 && (
        <EmptyState
          icon={Target}
          title="No concepts yet for this course"
          action={
            <Link to="/courses" className="btn-primary">
              Add material
            </Link>
          }
        >
          Once your material is processed, the Coach tracks how well you know every topic in it.
        </EmptyState>
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
              <StatTile key={label as string} label={label as string} value={value as number} />
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
            <section className="mt-5 rounded-xl border border-gold bg-gradient-to-br from-gold/15 to-gold/5 p-4">
              <h2 className="flex items-center gap-2 font-semibold text-navy">
                <Lightbulb className="h-4 w-4 text-gold-dark" aria-hidden /> Revise these next
              </h2>
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
                Open a topic above to revise it, or generate a cumulative quiz from{" "}
                <Link to="/study" className="font-semibold text-gold-dark">
                  Study Engine
                </Link>{" "}
                to practise all of them together.
              </p>
            </section>
          )}

          <section className="mt-6">
            <h2 className="section-title">
              <ListTree className="h-3.5 w-3.5" aria-hidden /> All concepts
            </h2>
            <ul className="card flex flex-col gap-4 p-4">
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
