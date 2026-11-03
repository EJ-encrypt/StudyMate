import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Clock,
  FileQuestion,
  Gamepad2,
  Layers,
  ListChecks,
  Loader2,
  LucideIcon,
  PenLine,
  Play,
  RotateCcw,
  ScrollText,
  TextCursorInput,
  Upload,
} from "lucide-react";
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
import { Alert, StatusPill } from "../components/ui";

const KINDS: { kind: AssessmentKind; icon: LucideIcon; blurb: string }[] = [
  { kind: "flashcard", icon: Layers, blurb: "Quick recall cards" },
  { kind: "mcq", icon: ListChecks, blurb: "Four options each" },
  { kind: "fill_blank", icon: TextCursorInput, blurb: "Recall the key term" },
  { kind: "short_answer", icon: PenLine, blurb: "Marked by AI" },
  { kind: "exam", icon: ScrollText, blurb: "A mixed paper" },
];

const KIND_ICONS = Object.fromEntries(KINDS.map((k) => [k.kind, k.icon])) as Record<AssessmentKind, LucideIcon>;

function AssessmentStatusPill({ assessment }: { assessment: AssessmentSummary }) {
  switch (assessment.status) {
    case "pending":
      return (
        <StatusPill tone="grey">
          <Clock className="h-3 w-3" aria-hidden /> Queued
        </StatusPill>
      );
    case "processing":
      return (
        <StatusPill tone="blue">
          <Loader2 className="h-3 w-3 animate-spin" aria-hidden /> Writing
        </StatusPill>
      );
    case "completed":
      return (
        <StatusPill tone="green">
          <CheckCircle2 className="h-3 w-3" aria-hidden /> Ready
        </StatusPill>
      );
    default:
      return (
        <StatusPill tone="red">
          <AlertTriangle className="h-3 w-3" aria-hidden /> Failed
        </StatusPill>
      );
  }
}

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
    }, 4000);
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
      <Link to="/study" className="btn-ghost -ml-2 mb-2">
        <ArrowLeft className="h-4 w-4" aria-hidden /> All courses
      </Link>
      <PageHeader
        title={course ? `${course.code} — ${course.name}` : "Study"}
        subtitle={course ? `Level ${course.level} · Semester ${course.semester}` : undefined}
        actions={
          courseId && (
            <>
              <Link to={`/courses/${courseId}`} className="btn-secondary">
                <Upload className="h-4 w-4" aria-hidden /> Add material
              </Link>
              <Link to={`/play?course=${courseId}`} className="btn-gold">
                <Gamepad2 className="h-4 w-4" aria-hidden /> Play
              </Link>
            </>
          )
        }
      />

      {error && (
        <div className="mb-4">
          <Alert>{error}</Alert>
        </div>
      )}

      <section className="card mb-5 p-4">
        <h2 className="section-title">What this course covers</h2>
        {course?.summary ? (
          <p className="text-sm leading-relaxed text-navy/80">{course.summary}</p>
        ) : (
          <p className="text-sm text-navy/50">An overview appears once your material has been processed.</p>
        )}
        <p className="mt-3 text-xs text-navy/50">
          {ready.length} of {documents.length} file{documents.length === 1 ? "" : "s"} ready
        </p>
      </section>

      <section className="mb-6">
        <h2 className="section-title">Generate</h2>

        {ready.length === 0 ? (
          <p className="card p-4 text-sm text-navy/60">Nothing is ready yet. Material has to finish processing first.</p>
        ) : pendingKind === null ? (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            {KINDS.map(({ kind, icon: Icon, blurb }) => (
              <button
                key={kind}
                type="button"
                onClick={() => setPendingKind(kind)}
                className="card group flex flex-col items-start p-3 text-left transition hover:-translate-y-0.5 hover:border-gold hover:shadow-lift"
              >
                <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-navy text-gold group-hover:bg-navy-light">
                  <Icon className="h-[18px] w-[18px]" aria-hidden />
                </span>
                <span className="mt-2 text-sm font-semibold text-navy">{KIND_LABELS[kind]}</span>
                <span className="text-xs text-navy/50">{blurb}</span>
              </button>
            ))}
          </div>
        ) : (
          <div className="card animate-fade-in p-4">
            <p className="text-sm font-semibold text-navy">{KIND_LABELS[pendingKind]} — from what?</p>
            <div className="mt-3 flex flex-col gap-2">
              <button
                type="button"
                disabled={isBusy}
                onClick={() => generate(pendingKind, null)}
                className="w-full rounded-lg border border-gold bg-gold/10 px-3 py-2 text-left text-sm font-semibold text-navy hover:bg-gold/20 disabled:opacity-50"
              >
                The whole course
                <span className="ml-1 font-normal text-navy/60">— everything uploaded so far</span>
              </button>
              {ready.map((document) => (
                <button
                  key={document.id}
                  type="button"
                  disabled={isBusy}
                  onClick={() => generate(pendingKind, document.id)}
                  className="w-full truncate rounded-lg border border-navy/15 px-3 py-2 text-left text-sm text-navy hover:bg-navy/5 disabled:opacity-50"
                >
                  {document.filename}
                </button>
              ))}
              <button type="button" onClick={() => setPendingKind(null)} className="btn-ghost w-fit text-xs">
                Cancel
              </button>
            </div>
          </div>
        )}
      </section>

      {assessments.length > 0 && (
        <section>
          <h2 className="section-title">
            <FileQuestion className="h-3.5 w-3.5" aria-hidden /> Generated
          </h2>
          <ul className="card divide-y divide-navy/5">
            {assessments.map((assessment) => {
              const Icon = KIND_ICONS[assessment.kind];
              return (
                <li key={assessment.id} className="flex items-center justify-between gap-3 px-4 py-3">
                  <div className="flex min-w-0 items-start gap-3">
                    <Icon className="mt-0.5 h-4 w-4 shrink-0 text-navy/40" aria-hidden />
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-navy">{assessment.title}</p>
                      {assessment.status === "failed" && assessment.error_message && (
                        <p className="mt-0.5 text-xs text-red-600">{assessment.error_message}</p>
                      )}
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    {assessment.status === "completed" ? (
                      <Link to={`/quiz/${assessment.id}`} className="btn-primary px-3 py-1.5 text-xs">
                        <Play className="h-3.5 w-3.5" aria-hidden />
                        {assessment.kind === "flashcard" ? "Review" : "Start"}
                      </Link>
                    ) : (
                      <>
                        {assessment.status === "failed" && assessment.can_retry && (
                          <button
                            type="button"
                            onClick={async () => {
                              await retryAssessment(assessment.id);
                              await refresh();
                            }}
                            className="btn-ghost py-1 text-xs"
                          >
                            <RotateCcw className="h-3.5 w-3.5" aria-hidden /> Try again
                          </button>
                        )}
                        <AssessmentStatusPill assessment={assessment} />
                      </>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        </section>
      )}
    </>
  );
}
