import {
  AlertTriangle,
  ArrowLeft,
  Camera,
  CheckCircle2,
  Clock,
  FileText,
  Loader2,
  NotebookPen,
  RotateCcw,
  Brain,
  UploadCloud,
} from "lucide-react";
import { DragEvent, FormEvent, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { errorMessage } from "../api/client";
import { Course, getCourse } from "../api/courses";
import {
  DocumentSummary,
  createNotes,
  listDocuments,
  retryDocument,
  uploadDocuments,
} from "../api/documents";
import DeleteCourse from "../components/DeleteCourse";
import PageHeader from "../components/PageHeader";
import PhotoNotes from "../components/PhotoNotes";
import { Alert, EmptyState, StatusPill } from "../components/ui";

const ACCEPTED = ".pdf,.docx,.pptx,.txt,.md,.png,.jpg,.jpeg,.webp";
const MAX_BYTES = 20 * 1024 * 1024;

function DocumentStatusPill({ status }: { status: DocumentSummary["status"] }) {
  switch (status) {
    case "pending":
      return (
        <StatusPill tone="grey">
          <Clock className="h-3 w-3" aria-hidden /> Queued
        </StatusPill>
      );
    case "processing":
      return (
        <StatusPill tone="blue">
          <Loader2 className="h-3 w-3 animate-spin" aria-hidden /> Reading
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

type Mode = "files" | "notes" | "photos";

const MODES: { mode: Mode; label: string; icon: typeof Camera }[] = [
  { mode: "files", label: "Upload files", icon: UploadCloud },
  { mode: "notes", label: "Type notes", icon: NotebookPen },
  { mode: "photos", label: "Photograph notes", icon: Camera },
];

export default function CourseDetail() {
  const { courseId } = useParams<{ courseId: string }>();
  const [course, setCourse] = useState<Course | null>(null);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [mode, setMode] = useState<Mode>("files");
  const [files, setFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [progress, setProgress] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

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
    }, 4000);
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documents]);

  function choose(selected: File[]) {
    setError(null);
    const tooBig = selected.find((file) => file.size > MAX_BYTES);
    if (tooBig) {
      setError(`${tooBig.name} is larger than 20MB. Split it, or export the slides as PDF.`);
      return;
    }
    setFiles(selected);
  }

  function handleDrop(event: DragEvent) {
    event.preventDefault();
    setIsDragging(false);
    choose(Array.from(event.dataTransfer.files));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!courseId) return;

    setIsBusy(true);
    setError(null);
    setNotice(null);
    try {
      if (mode === "files") {
        setProgress(`Uploading 0 of ${files.length}...`);
        const added = await uploadDocuments(courseId, files, (done, total) =>
          setProgress(`Uploading ${done} of ${total}...`),
        );
        setNotice(`Added ${added.length} file${added.length === 1 ? "" : "s"}. StudyMate is reading them now.`);
        setFiles([]);
        if (fileInput.current) fileInput.current.value = "";
      } else {
        await createNotes(courseId, title.trim(), content);
        setNotice("Notes saved. StudyMate is reading them now.");
        setTitle("");
        setContent("");
      }
      await refresh();
    } catch (err) {
      setError(
        errorMessage(
          err,
          mode === "files"
            ? "Upload failed. Supported: PDF, DOCX, PPTX, TXT, MD and photos (max 20MB each)."
            : "Could not save those notes.",
        ),
      );
    } finally {
      setIsBusy(false);
      setProgress(null);
    }
  }

  const canSubmit = !isBusy && (mode === "files" ? files.length > 0 : !!title.trim() && !!content.trim());
  const anyReady = documents.some((d) => d.status === "completed");

  return (
    <>
      <Link to="/courses" className="btn-ghost -ml-2 mb-2">
        <ArrowLeft className="h-4 w-4" aria-hidden /> All courses
      </Link>
      <PageHeader
        title={course ? `${course.code} — ${course.name}` : "Course"}
        subtitle={course ? `Level ${course.level} · Semester ${course.semester}` : undefined}
        actions={
          anyReady &&
          courseId && (
            <Link to={`/study/${courseId}`} className="btn-primary">
              <Brain className="h-4 w-4" aria-hidden /> Study this course
            </Link>
          )
        }
      />

      <section className="card mb-6 p-4">
        <div className="mb-4 flex w-full rounded-lg bg-ink/5 p-1 sm:inline-flex sm:w-auto" role="tablist">
          {MODES.map(({ mode: option, label, icon: Icon }) => (
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
              className={[
                "flex flex-1 flex-col items-center gap-0.5 rounded-md px-2 py-1.5 text-xs font-semibold transition sm:flex-none sm:flex-row sm:gap-1.5 sm:px-3 sm:text-sm",
                mode === option ? "bg-surface text-ink shadow-sm" : "text-ink/60 hover:text-ink",
              ].join(" ")}
            >
              <Icon className="h-4 w-4" aria-hidden />
              {label}
            </button>
          ))}
        </div>

        {mode === "photos" && courseId ? (
          <PhotoNotes courseId={courseId} onUploaded={refresh} />
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            {mode === "files" ? (
              <>
                <label
                  onDragOver={(e) => {
                    e.preventDefault();
                    setIsDragging(true);
                  }}
                  onDragLeave={() => setIsDragging(false)}
                  onDrop={handleDrop}
                  className={[
                    "flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-4 py-8 text-center transition",
                    isDragging ? "border-gold bg-gold/10" : "border-ink/15 hover:border-gold/60 hover:bg-gold/5",
                  ].join(" ")}
                >
                  <UploadCloud className="h-8 w-8 text-gold-dark" aria-hidden />
                  <span className="mt-2 text-sm font-semibold text-ink">Drop files here, or tap to choose</span>
                  <span className="mt-0.5 text-xs text-ink/50">PDF, slides, Word, notes or photos of notes · up to 20MB each</span>
                  <input
                    ref={fileInput}
                    id="file-input"
                    type="file"
                    multiple
                    accept={ACCEPTED}
                    onChange={(e) => choose(Array.from(e.target.files ?? []))}
                    className="sr-only"
                  />
                </label>
                {files.length > 0 && (
                  <ul className="space-y-1">
                    {files.map((file) => (
                      <li key={file.name} className="flex items-center gap-2 text-sm text-ink/75">
                        <FileText className="h-4 w-4 text-ink/40" aria-hidden />
                        <span className="truncate">{file.name}</span>
                        <span className="text-xs text-ink/40">{(file.size / 1024 / 1024).toFixed(1)}MB</span>
                      </li>
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
                  className="input"
                />
                <textarea
                  placeholder="Paste or type your notes..."
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  rows={8}
                  className="input font-mono"
                />
              </>
            )}

            {error && <Alert>{error}</Alert>}
            {notice && <Alert kind="success">{notice}</Alert>}

            <button type="submit" disabled={!canSubmit} className="btn-primary w-fit">
              {isBusy && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
              {isBusy ? progress ?? "Saving..." : mode === "files" ? "Upload" : "Save notes"}
            </button>
          </form>
        )}
      </section>

      <h2 className="section-title">
        <FileText className="h-3.5 w-3.5" aria-hidden /> Material ({documents.length})
      </h2>

      {documents.length === 0 ? (
        <EmptyState icon={FileText} title="Nothing uploaded yet">
          Upload lecture slides, PDFs, notes or photos of handwritten notes above. StudyMate reads them, equations included, and pulls out the key concepts.
        </EmptyState>
      ) : (
        <ul className="card divide-y divide-ink/5">
          {documents.map((document) => (
            <li key={document.id} className="px-4 py-3">
              <div className="flex items-start justify-between gap-3">
                <div className="flex min-w-0 items-start gap-3">
                  <FileText className="mt-0.5 h-4 w-4 shrink-0 text-ink/40" aria-hidden />
                  <p className="truncate text-sm font-semibold text-ink">{document.filename}</p>
                </div>
                <DocumentStatusPill status={document.status} />
              </div>
              {document.status === "failed" && (document.error_message || document.can_retry) && (
                <div className="ml-7 mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
                  {document.error_message && <p className="text-xs text-red-600">{document.error_message}</p>}
                  {document.can_retry && (
                    <button
                      type="button"
                      onClick={async () => {
                        await retryDocument(document.id);
                        await refresh();
                      }}
                      className="btn-ghost -ml-2 py-1 text-xs"
                    >
                      <RotateCcw className="h-3.5 w-3.5" aria-hidden /> Try again
                    </button>
                  )}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}

      {course && <DeleteCourse course={course} />}
    </>
  );
}
