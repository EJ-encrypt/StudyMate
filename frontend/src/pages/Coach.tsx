import { BookOpenCheck, Lightbulb, ListTree } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import {
  CoachSummary,
  ConceptStatus,
  getCoachSummary,
  STATUS_LABELS,
  STATUS_STYLES,
} from "../api/coach";
import CourseSelect from "../components/CourseSelect";
import MathText from "../components/MathText";
import PageHeader from "../components/PageHeader";
import { Alert, EmptyState, StatTile } from "../components/ui";
import { CoachIcon } from "../lib/icons";

function StatusBadge({ status }: { status: ConceptStatus }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${STATUS_STYLES[status]}`}>
      {STATUS_LABELS[status]}
    </span>
  );
}

function MasteryBar({ score }: { score: number | null }) {
  if (score === null) {
    return <div className="h-2 w-full rounded-full bg-ink/10" />;
  }
  const percent = Math.round(score * 100);
  const colour = score < 0.5 ? "bg-red-500" : score < 0.8 ? "bg-gold" : "bg-green-600";
  return (
    <div className="h-2 w-full rounded-full bg-ink/10">
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
        icon={CoachIcon}
        title="Coach"
        subtitle="How well you know each topic, from the questions you have answered."
      />

      <div className="mb-4">
        <CourseSelect selectedCourseId={courseId} onSelect={setCourseId} allowCreate={false} />
      </div>

      {error && <Alert>{error}</Alert>}

      {summary && summary.concept_count === 0 && (
        <EmptyState
          icon={CoachIcon}
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
            <p className="mt-4 text-sm text-ink/70">
              Overall mastery across practised concepts:{" "}
              <span className="font-semibold text-ink">
                {Math.round(summary.overall_mastery * 100)}%
              </span>
            </p>
          )}

          {summary.topics.length > 0 && (
            <section className="mt-5 rounded-xl border border-gold bg-gradient-to-br from-gold/15 to-gold/5 p-4">
              <h2 className="flex items-center gap-2 font-semibold text-ink">
                <Lightbulb className="h-4 w-4 text-gold-dark" aria-hidden /> Revise these next
              </h2>
              <p className="mt-1 text-sm text-ink/65">
                {summary.topics.length === 1
                  ? "One topic to focus on."
                  : `${summary.topics.length} topics to focus on. Related ideas are grouped, so each one is a single revision session.`}
              </p>
              <ol className="mt-3 grid gap-3">
                {summary.topics.map((topic, index) => (
                  <li key={topic.title + index} className="rounded-lg border border-ink/10 bg-surface/80 p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-navy text-xs font-bold text-gold">
                        {index + 1}
                      </span>
                      <span className="font-semibold text-ink">
                        {topic.title}
                        {topic.concepts.length > 1 && (
                          <span className="font-normal text-ink/55"> and {topic.concepts.length - 1} related</span>
                        )}
                      </span>
                      <StatusBadge status={topic.status} />
                    </div>
                    <p className="mt-1 text-sm text-ink/70">
                      <MathText text={topic.summary} />
                    </p>
                    {topic.concepts.length > 1 && (
                      <ul className="mt-2 flex flex-wrap gap-1.5">
                        {topic.concepts.map((concept) => (
                          <li key={concept.concept_id}>
                            <Link
                              to={`/coach/concept/${concept.concept_id}`}
                              className="inline-flex rounded-full border border-ink/15 px-2.5 py-0.5 text-xs text-ink/80 hover:border-gold hover:bg-gold/10"
                            >
                              {concept.name}
                            </Link>
                          </li>
                        ))}
                      </ul>
                    )}
                    {topic.concepts.length === 1 && (
                      <Link
                        to={`/coach/concept/${topic.concepts[0].concept_id}`}
                        className="mt-2 inline-flex text-xs font-semibold text-gold-dark hover:underline"
                      >
                        Open this topic
                      </Link>
                    )}
                  </li>
                ))}
              </ol>
              <p className="mt-4 flex items-start gap-1.5 text-sm text-ink/70">
                <BookOpenCheck className="mt-0.5 h-4 w-4 shrink-0 text-gold-dark" aria-hidden />
                <span>
                  Tap a concept to revise it, or generate a whole-course quiz in the{" "}
                  <Link to={`/study/${summary.course_id}`} className="font-semibold text-gold-dark">
                    Study Engine
                  </Link>{" "}
                  to practise these together.
                  {summary.more_to_revise > 0 &&
                    ` Once these improve, ${summary.more_to_revise} more concept${summary.more_to_revise === 1 ? "" : "s"} will move up from the list below.`}
                </span>
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
                    <span className="font-semibold text-ink">{concept.name}</span>
                    <div className="flex items-center gap-2">
                      {concept.attempts > 0 && (
                        <span className="text-xs text-ink/60">
                          {concept.correct}/{concept.attempts} correct
                        </span>
                      )}
                      <StatusBadge status={concept.status} />
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
