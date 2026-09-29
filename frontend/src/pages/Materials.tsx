import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import {
  AssessmentKind,
  AssessmentSummary,
  createAssessment,
  createCumulativeAssessment,
  KIND_LABELS,
  listAssessments,
  retryAssessment,
} from "../api/assessments";
import { CourseConcept, listCourseConcepts } from "../api/courses";
import {
  DocumentDetail,
  DocumentSummary,
  getDocument,
  listDocuments,
  retryDocument,
} from "../api/documents";
import CourseSelect from "../components/CourseSelect";

const STATUS_LABEL: Record<DocumentSummary["status"], string> = {
  pending: "Queued",
  processing: "Extracting concepts...",
  completed: "Done",
  failed: "Failed",
};

const KINDS: AssessmentKind[] = ["flashcard", "mcq", "fill_blank", "short_answer", "exam"];

export default function Materials() {
  const [courseId, setCourseId] = useState<string | null>(null);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [assessments, setAssessments] = useState<AssessmentSummary[]>([]);
  const [selected, setSelected] = useState<DocumentDetail | null>(null);
  const [busyDocumentId, setBusyDocumentId] = useState<string | null>(null);
  const [knowledgeBase, setKnowledgeBase] = useState<CourseConcept[]>([]);
  const [isGeneratingCumulative, setIsGeneratingCumulative] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    if (!courseId) return;
    const [fetchedDocuments, fetchedAssessments, fetchedConcepts] = await Promise.all([
      listDocuments(courseId),
      listAssessments(courseId),
      listCourseConcepts(courseId),
    ]);
    setDocuments(fetchedDocuments);
    setAssessments(fetchedAssessments);
    setKnowledgeBase(fetchedConcepts);
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [courseId]);

  async function viewConcepts(documentId: string) {
    setSelected(await getDocument(documentId));
  }

  async function generate(documentId: string, kind: AssessmentKind) {
    setBusyDocumentId(documentId);
    setError(null);
    try {
      await createAssessment(documentId, kind);
      await refresh();
    } catch {
      setError("Could not start generation. Make sure the document finished processing.");
    } finally {
      setBusyDocumentId(null);
    }
  }

  async function retry(kind: "document" | "assessment", id: string) {
    setError(null);
    try {
      if (kind === "document") {
        await retryDocument(id);
      } else {
        await retryAssessment(id);
      }
      await refresh();
    } catch {
      setError("Could not try that again just yet. Wait a moment and retry.");
    }
  }

  async function generateCumulative(kind: AssessmentKind) {
    if (!courseId) return;
    setIsGeneratingCumulative(true);
    setError(null);
    try {
      await createCumulativeAssessment(courseId, kind);
      await refresh();
    } catch {
      setError("Could not start a cumulative assessment for this course.");
    } finally {
      setIsGeneratingCumulative(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="text-2xl font-bold text-navy">Materials</h1>

      <div className="mt-6 flex items-center justify-between gap-4">
        <CourseSelect selectedCourseId={courseId} onSelect={setCourseId} />
        <button
          type="button"
          onClick={refresh}
          className="rounded border border-navy/20 px-3 py-1.5 text-sm font-semibold text-navy hover:bg-navy/5"
        >
          Refresh
        </button>
      </div>

      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}

      <ul className="mt-6 divide-y divide-navy/10">
        {documents.length === 0 && <p className="text-navy/70">No documents uploaded for this course yet.</p>}
        {documents.map((document) => (
          <li key={document.id} className="py-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="font-semibold text-navy">{document.filename}</p>
                <p className="text-sm text-navy/60">{STATUS_LABEL[document.status]}</p>
                {document.status === "failed" && (
                  <>
                    {document.error_message && (
                      <p className="text-sm text-red-600">{document.error_message}</p>
                    )}
                    {document.can_retry && (
                      <button
                        type="button"
                        onClick={() => retry("document", document.id)}
                        className="mt-1 text-sm font-semibold text-gold-dark hover:underline"
                      >
                        Try again
                      </button>
                    )}
                  </>
                )}
              </div>
              {document.status === "completed" && (
                <button
                  type="button"
                  onClick={() => viewConcepts(document.id)}
                  className="whitespace-nowrap text-sm font-semibold text-gold-dark hover:underline"
                >
                  View concepts
                </button>
              )}
            </div>

            {document.status === "completed" && (
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <span className="text-sm text-navy/60">Generate:</span>
                {KINDS.map((kind) => (
                  <button
                    key={kind}
                    type="button"
                    disabled={busyDocumentId === document.id}
                    onClick={() => generate(document.id, kind)}
                    className="rounded border border-navy/20 px-3 py-1 text-sm font-semibold text-navy hover:bg-navy/5 disabled:opacity-50"
                  >
                    {KIND_LABELS[kind]}
                  </button>
                ))}
              </div>
            )}
          </li>
        ))}
      </ul>

      {knowledgeBase.length > 0 && (
        <section className="mt-10 rounded border border-navy/10 p-4">
          <h2 className="font-semibold text-navy">
            Course knowledge base
            <span className="ml-2 text-sm font-normal text-navy/60">
              {knowledgeBase.length} concepts across {documents.length} documents
            </span>
          </h2>
          <p className="mt-1 text-sm text-navy/70">
            Concepts from every document you have uploaded for this course, merged so a topic
            taught in more than one lecture appears once.
          </p>

          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span className="text-sm text-navy/60">Cumulative:</span>
            {KINDS.map((kind) => (
              <button
                key={kind}
                type="button"
                disabled={isGeneratingCumulative}
                onClick={() => generateCumulative(kind)}
                className="rounded border border-gold px-3 py-1 text-sm font-semibold text-navy hover:bg-gold/10 disabled:opacity-50"
              >
                {KIND_LABELS[kind]}
              </button>
            ))}
          </div>

          <ul className="mt-4 flex flex-col gap-2">
            {knowledgeBase.map((concept) => (
              <li key={concept.id}>
                <p className="font-semibold text-navy">
                  {concept.name}
                  {concept.document_count > 1 && (
                    <span className="ml-2 rounded bg-gold/20 px-2 py-0.5 text-xs font-normal text-navy/70">
                      in {concept.document_count} documents
                    </span>
                  )}
                </p>
                <p className="text-sm text-navy/70">{concept.summary}</p>
              </li>
            ))}
          </ul>
        </section>
      )}

      {assessments.length > 0 && (
        <section className="mt-10">
          <h2 className="font-semibold text-navy">Assessments</h2>
          <ul className="mt-3 divide-y divide-navy/10">
            {assessments.map((assessment) => (
              <li key={assessment.id} className="flex items-center justify-between gap-4 py-3">
                <div>
                  <p className="font-semibold text-navy">{assessment.title}</p>
                  <p className="text-sm text-navy/60">
                    {KIND_LABELS[assessment.kind]} &middot; {assessment.status}
                  </p>
                  {assessment.status === "failed" && (
                    <>
                      {assessment.error_message && (
                        <p className="text-sm text-red-600">{assessment.error_message}</p>
                      )}
                      {assessment.can_retry && (
                        <button
                          type="button"
                          onClick={() => retry("assessment", assessment.id)}
                          className="mt-1 text-sm font-semibold text-gold-dark hover:underline"
                        >
                          Try again
                        </button>
                      )}
                    </>
                  )}
                </div>
                {assessment.status === "completed" && (
                  <Link
                    to={`/quiz/${assessment.id}`}
                    className="whitespace-nowrap text-sm font-semibold text-gold-dark hover:underline"
                  >
                    {assessment.kind === "flashcard" ? "Review" : "Take quiz"}
                  </Link>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {selected && (
        <div className="mt-8 rounded border border-navy/10 p-4">
          <h2 className="font-semibold text-navy">{selected.filename} - Key Concepts</h2>
          <ul className="mt-3 flex flex-col gap-3">
            {selected.concepts.map((concept) => (
              <li key={concept.id}>
                <p className="font-semibold text-navy">{concept.name}</p>
                <p className="text-sm text-navy/70">{concept.summary}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
