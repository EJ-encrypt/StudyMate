import { ArrowRight, BookOpenCheck, Layers, Lightbulb } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { CoachSummary, getCoachSummary } from "../api/coach";
import { getDueByCourse } from "../api/review";
import CourseSelect from "../components/CourseSelect";
import PageHeader from "../components/PageHeader";
import RevisionTopicCard from "../components/RevisionTopicCard";
import { Alert, EmptyState, StatTile } from "../components/ui";
import { CoachIcon } from "../lib/icons";

export default function Coach() {
  const [courseId, setCourseId] = useState<string | null>(null);
  const [summary, setSummary] = useState<CoachSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dueCards, setDueCards] = useState(0);

  useEffect(() => {
    if (!courseId) return;
    getDueByCourse()
      .then((courses) => setDueCards(courses.find((c) => c.course_id === courseId)?.due ?? 0))
      .catch(() => setDueCards(0));
  }, [courseId]);

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
        <CourseSelect selectedCourseId={courseId} onSelect={setCourseId} />
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

      {dueCards > 0 && courseId && (
        <Link
          to={`/review/${courseId}`}
          className="mb-4 flex items-center gap-3 rounded-xl border border-gold/50 bg-gold/10 p-4 transition hover:bg-gold/15"
        >
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gold/25 text-gold-dark">
            <Layers className="h-5 w-5" aria-hidden />
          </span>
          <span className="min-w-0 flex-1">
            <span className="block font-semibold text-ink">
              {dueCards} flashcard{dueCards === 1 ? "" : "s"} due for review
            </span>
            <span className="block text-sm text-ink/60">A few minutes now keeps them from slipping.</span>
          </span>
          <ArrowRight className="h-5 w-5 shrink-0 text-gold-dark" aria-hidden />
        </Link>
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

          {summary.topics.length === 0 && (
            <div className="mt-5">
              <Alert kind="success">
                Every concept in this course is strong. Keep it fresh with a whole-course quiz or an Arcade round now
                and then.
              </Alert>
            </div>
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
                  <RevisionTopicCard key={topic.title + index} courseId={summary.course_id} topic={topic} number={index + 1} />
                ))}
              </ol>
              <p className="mt-4 flex items-start gap-1.5 text-sm text-ink/70">
                <BookOpenCheck className="mt-0.5 h-4 w-4 shrink-0 text-gold-dark" aria-hidden />
                <span>
                  Open a topic to see where each idea is explained in your material and how they fit together.
                  Then generate a whole-course quiz in the{" "}
                  <Link to={`/study/${summary.course_id}`} className="font-semibold text-gold-dark">
                    Study Engine
                  </Link>{" "}
                  to practise these together.
                  {summary.more_to_revise > 0 &&
                    ` Once these improve, ${summary.more_to_revise} more concept${summary.more_to_revise === 1 ? "" : "s"} will move up here.`}
                </span>
              </p>
            </section>
          )}

        </>
      )}
    </>
  );
}
