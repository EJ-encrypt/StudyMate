import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  AssessmentKind,
  AssessmentSummary,
  KIND_LABELS,
  createAssessment,
  createCumulativeAssessment,
  listAssessments,
  retryAssessment,
} from "../api/assessments";
import { Course, getCourse } from "../api/courses";
import { DocumentSummary, listDocuments } from "../api/documents";
import PageHeader from "../components/PageHeader";

const KINDS: AssessmentKind[] = ["flashcard", "mcq", "fill_blank", "short_answer", "exam"];

export default function StudyCourse() {
  const { courseId } = useParams<{ courseId: string }>();
  const [course, setCourse] = useState<Course | null>(null);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [assessments, setAssessments] = useState<AssessmentSummary[]>([]);
  // Which action the student clicked, while they choose its scope.
  const [pendingKind, setPendingKind] = useState<AssessmentKind | null>(null);
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    if (!courseId) return;
    const [fetchedDocuments, fetchedAssessments, fetchedCourse] = await Promise.all([
      listDocuments(courseId),
      listAssessments(courseId),
      getCourse(courseId),
    ]);
    setDocuments(fetchedDocuments);
    setAssessments(fetchedAssessments);
    setCourse(fetchedCourse);
  }

  useEffect(() => {
    refresh().catch(() => setError("Could not load this course."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [courseId]);

  useEffect(() => {
    const working = assessments.some((a) => a.status === "pending" || a.status === "processing");
    if (!working) return;
    const timer = setInterval(() => {
      refresh().catch(() => undefined);
    }, 5000);
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assessments]);

  async function generate(kind: AssessmentKind, documentId: string | null) {
    if (!courseId) return;
    setIsBusy(true);
    setError(null);
    try {
      if (documentId) {
        await createAssessment(documentId, kind);
      } else {
        await createCumulativeAssessment(courseId, kind);
      }
      setPendingKind(null);
      await refresh();
    } catch {
      setError("Could not start that. Make sure the material has finished processing.");
    } finally {
      setIsBusy(false);
    }
  }

  const ready = documents.filter((d) => d.status === "completed");

  return (
    <>
      <PageHeader
        title={course ? `${course.code} — ${course.name}` : "Study"}
        subtitle={course ? `Level ${course.level} · Semester ${course.semester}` : undefined}
        actions={
          <>
            <Link
              to="/study"
              className="rounded border border-navy/20 px-3 py-1.5 text-sm font-semibold text-navy hover:bg-navy/5"
            >
              All courses
            </Link>
            {courseId && (
              <Link
                to={`/courses/${courseId}`}
                className="rounded border border-navy/20 px-3 py-1.5 text-sm font-semibold text-navy hover:bg-navy/5"
              >
                Add material
              </Link>
            )}
          </>
        }
      />

      {error && <p className="mb-3 text-sm text-red-600">{error}</p>}

      <section className="mb-4 rounded border border-navy/15 bg-white p-3">
        <h2 className="text-xs font-bold uppercase tracking-wide text-navy/50">
          What this course covers
        </h2>
        {course?.summary ? (
          <p className="mt-1 text-sm text-navy/80">{course.summary}</p>
        ) : (
          <p className="mt-1 text-sm text-navy/50">
            An overview appears once your material has been processed.
          </p>
        )}
        <p className="mt-2 text-xs text-navy/50">
          {ready.length} of {documents.length} file{documents.length === 1 ? "" : "s"} ready
        </p>
      </section>

      <section className="mb-5 rounded border border-navy/15 bg-white p-3">
        <h2 className="mb-2 text-xs font-bold uppercase tracking-wide text-navy/50">Generate</h2>

        {ready.length === 0 ? (
          <p className="text-sm text-navy/60">
            Nothing is ready yet. Material has to finish processing first.
          </p>
        ) : pendingKind === null ? (
          <div className="flex flex-wrap gap-2">
            {KINDS.map((kind) => (
              <button
                key={kind}
                type="button"
                onClick={() => setPendingKind(kind)}
                className="rounded border border-navy/20 px-3 py-1.5 text-sm font-semibold text-navy hover:border-gold hover:bg-gold/10"
              >
                {KIND_LABELS[kind]}
              </button>
            ))}
          </div>
        ) : (
          <div>
            <p className="text-sm font-semibold text-navy">
              {KIND_LABELS[pendingKind]} — from what?
            </p>
            <div className="mt-2 flex flex-col gap-1.5">
              <button
                type="button"
                disabled={isBusy}
                onClick={() => generate(pendingKind, null)}
                className="w-full rounded border border-gold bg-gold/10 px-3 py-1.5 text-left text-sm font-semibold text-navy hover:bg-gold/20 disabled:opacity-50"
              >
                The whole course
                <span className="ml-1 font-normal text-navy/60">
                  — everything uploaded so far
                </span>
              </button>
              {ready.map((document) => (
                <button
                  key={document.id}
                  type="button"
                  disabled={isBusy}
                  onClick={() => generate(pendingKind, document.id)}
                  className="w-full truncate rounded border border-navy/20 px-3 py-1.5 text-left text-sm text-navy hover:bg-navy/5 disabled:opacity-50"
                >
                  {document.filename}
                </button>
              ))}
              <button
                type="button"
                onClick={() => setPendingKind(null)}
                className="w-fit text-xs font-semibold text-navy/60 hover:underline"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </section>

      {assessments.length > 0 && (
        <section>
          <h2 className="mb-2 text-xs font-bold uppercase tracking-wide text-navy/50">
            Generated
          </h2>
          <ul className="divide-y divide-navy/10 rounded border border-navy/15 bg-white">
            {assessments.map((assessment) => (
              <li
                key={assessment.id}
                className="flex items-start justify-between gap-3 px-3 py-2"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-navy">{assessment.title}</p>
                  <p className="text-xs text-navy/50">
                    {KIND_LABELS[assessment.kind]} · {assessment.status}
                  </p>
                  {assessment.status === "failed" && assessment.error_message && (
                    <p className="text-xs text-red-600">{assessment.error_message}</p>
                  )}
                </div>
                {assessment.status === "completed" ? (
                  <Link
                    to={`/quiz/${assessment.id}`}
                    className="whitespace-nowrap text-xs font-semibold text-gold-dark hover:underline"
                  >
                    {assessment.kind === "flashcard" ? "Review" : "Start"}
                  </Link>
                ) : (
                  assessment.status === "failed" &&
                  assessment.can_retry && (
                    <button
                      type="button"
                      onClick={async () => {
                        await retryAssessment(assessment.id);
                        await refresh();
                      }}
                      className="whitespace-nowrap text-xs font-semibold text-gold-dark hover:underline"
                    >
                      Try again
                    </button>
                  )
                )}
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}
