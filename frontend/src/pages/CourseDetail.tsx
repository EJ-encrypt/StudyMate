import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { Course, getCourse } from "../api/courses";
import {
  DocumentSummary,
  createNotes,
  listDocuments,
  retryDocument,
  uploadDocuments,
} from "../api/documents";
import PageHeader from "../components/PageHeader";

const ACCEPTED = ".pdf,.docx,.pptx,.txt,.md";

const STATUS_LABEL: Record<DocumentSummary["status"], string> = {
  pending: "Queued",
  processing: "Reading...",
  completed: "Ready",
  failed: "Failed",
};

type Mode = "files" | "notes";

export default function CourseDetail() {
  const { courseId } = useParams<{ courseId: string }>();
  const [course, setCourse] = useState<Course | null>(null);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [mode, setMode] = useState<Mode>("files");
  const [files, setFiles] = useState<File[]>([]);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function refresh() {
    if (!courseId) return;
    setDocuments(await listDocuments(courseId));
  }

  useEffect(() => {
    if (!courseId) return;
    getCourse(courseId).then(setCourse).catch(() => setError("Could not load this course."));
    refresh().catch(() => setError("Could not load the material for this course."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [courseId]);

  // Anything still being read will change state shortly, so poll while it does.
  useEffect(() => {
    const working = documents.some((d) => d.status === "pending" || d.status === "processing");
    if (!working) return;
    const timer = setInterval(() => {
      refresh().catch(() => undefined);
    }, 5000);
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documents]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!courseId) return;

    setIsBusy(true);
    setError(null);
    setNotice(null);
    try {
      if (mode === "files") {
        const added = await uploadDocuments(courseId, files);
        setNotice(`Added ${added.length} file${added.length === 1 ? "" : "s"}.`);
        setFiles([]);
        (document.getElementById("file-input") as HTMLInputElement | null)?.value &&
          ((document.getElementById("file-input") as HTMLInputElement).value = "");
      } else {
        await createNotes(courseId, title.trim(), content);
        setNotice("Notes saved.");
        setTitle("");
        setContent("");
      }
      await refresh();
    } catch {
      setError(
        mode === "files"
          ? "Upload failed. Supported: PDF, DOCX, PPTX, TXT, MD (max 20MB each)."
          : "Could not save those notes.",
      );
    } finally {
      setIsBusy(false);
    }
  }

  const canSubmit =
    !isBusy && (mode === "files" ? files.length > 0 : !!title.trim() && !!content.trim());

  return (
    <>
      <PageHeader
        title={course ? `${course.code} — ${course.name}` : "Course"}
        subtitle={
          course ? `Level ${course.level} · Semester ${course.semester}` : undefined
        }
        actions={
          <>
            <Link
              to="/courses"
              className="rounded border border-navy/20 px-3 py-1.5 text-sm font-semibold text-navy hover:bg-navy/5"
            >
              All courses
            </Link>
            {documents.some((d) => d.status === "completed") && courseId && (
              <Link
                to={`/study/${courseId}`}
                className="rounded bg-navy px-3 py-1.5 text-sm font-semibold text-gold hover:bg-navy-light"
              >
                Study this course
              </Link>
            )}
          </>
        }
      />

      <section className="mb-5 rounded border border-navy/15 bg-white p-3">
        <div className="mb-3 flex gap-1" role="tablist">
          {(["files", "notes"] as Mode[]).map((option) => (
            <button
              key={option}
              type="button"
              role="tab"
              aria-selected={mode === option}
              onClick={() => {
                setMode(option);
                setError(null);
                setNotice(null);
              }}
              className={
                mode === option
                  ? "rounded bg-navy px-3 py-1 text-sm font-semibold text-gold"
                  : "rounded border border-navy/20 px-3 py-1 text-sm font-semibold text-navy hover:bg-navy/5"
              }
            >
              {option === "files" ? "Upload files" : "Type notes"}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-2">
          {mode === "files" ? (
            <>
              <input
                id="file-input"
                type="file"
                multiple
                accept={ACCEPTED}
                onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
                className="rounded border border-navy/20 px-2 py-1.5 text-sm"
              />
              <p className="text-xs text-navy/50">
                Select several at once. PDF, DOCX, PPTX, TXT or MD, up to 20MB each.
              </p>
              {files.length > 0 && (
                <ul className="text-xs text-navy/70">
                  {files.map((file) => (
                    <li key={file.name}>{file.name}</li>
                  ))}
                </ul>
              )}
            </>
          ) : (
            <>
              <input
                type="text"
                placeholder="Title, e.g. Week 5 - Normalization"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                maxLength={120}
                className="rounded border border-navy/20 px-2 py-1.5 text-sm"
              />
              <textarea
                placeholder="Paste or type your notes..."
                value={content}
                onChange={(e) => setContent(e.target.value)}
                rows={8}
                className="rounded border border-navy/20 px-2 py-1.5 font-mono text-sm"
              />
            </>
          )}

          {error && <p className="text-sm text-red-600">{error}</p>}
          {notice && <p className="text-sm text-green-700">{notice}</p>}

          <button
            type="submit"
            disabled={!canSubmit}
            className="w-fit rounded bg-navy px-3 py-1.5 text-sm font-semibold text-gold hover:bg-navy-light disabled:opacity-50"
          >
            {isBusy ? "Saving..." : mode === "files" ? "Upload" : "Save notes"}
          </button>
        </form>
      </section>

      <h2 className="mb-2 text-xs font-bold uppercase tracking-wide text-navy/50">
        Material ({documents.length})
      </h2>

      {documents.length === 0 ? (
        <p className="text-sm text-navy/60">Nothing uploaded for this course yet.</p>
      ) : (
        <ul className="divide-y divide-navy/10 rounded border border-navy/15 bg-white">
          {documents.map((document) => (
            <li key={document.id} className="flex items-start justify-between gap-3 px-3 py-2">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-navy">{document.filename}</p>
                {document.status === "failed" && document.error_message ? (
                  <p className="text-xs text-red-600">{document.error_message}</p>
                ) : (
                  <p className="text-xs text-navy/50">{STATUS_LABEL[document.status]}</p>
                )}
              </div>
              {document.status === "failed" && document.can_retry && (
                <button
                  type="button"
                  onClick={async () => {
                    await retryDocument(document.id);
                    await refresh();
                  }}
                  className="whitespace-nowrap text-xs font-semibold text-gold-dark hover:underline"
                >
                  Try again
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
