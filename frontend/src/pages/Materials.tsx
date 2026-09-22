import { useEffect, useState } from "react";

import { DocumentDetail, DocumentSummary, getDocument, listDocuments } from "../api/documents";
import CourseSelect from "../components/CourseSelect";

const STATUS_LABEL: Record<DocumentSummary["status"], string> = {
  pending: "Queued",
  processing: "Extracting concepts...",
  completed: "Done",
  failed: "Failed",
};

export default function Materials() {
  const [courseId, setCourseId] = useState<string | null>(null);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [selected, setSelected] = useState<DocumentDetail | null>(null);

  async function refresh() {
    if (!courseId) return;
    const fetched = await listDocuments(courseId);
    setDocuments(fetched);
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [courseId]);

  async function viewConcepts(documentId: string) {
    const detail = await getDocument(documentId);
    setSelected(detail);
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

      <ul className="mt-6 divide-y divide-navy/10">
        {documents.length === 0 && <p className="text-navy/70">No documents uploaded for this course yet.</p>}
        {documents.map((document) => (
          <li key={document.id} className="flex items-center justify-between gap-4 py-3">
            <div>
              <p className="font-semibold text-navy">{document.filename}</p>
              <p className="text-sm text-navy/60">{STATUS_LABEL[document.status]}</p>
              {document.status === "failed" && document.error_message && (
                <p className="text-sm text-red-600">{document.error_message}</p>
              )}
            </div>
            {document.status === "completed" && (
              <button
                type="button"
                onClick={() => viewConcepts(document.id)}
                className="text-sm font-semibold text-gold-dark hover:underline"
              >
                View concepts
              </button>
            )}
          </li>
        ))}
      </ul>

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
