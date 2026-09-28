import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";

import { createNotes, uploadDocument } from "../api/documents";
import CourseSelect from "../components/CourseSelect";

const ACCEPTED_EXTENSIONS = ".pdf,.docx,.pptx,.txt,.md";

type Mode = "file" | "notes";

export default function Upload() {
  const [courseId, setCourseId] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>("file");
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState<string | null>(null);

  const canSubmit =
    !!courseId && !isSubmitting && (mode === "file" ? !!file : !!title.trim() && !!content.trim());

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!courseId || !canSubmit) return;

    setIsSubmitting(true);
    setError(null);
    setSubmitted(null);
    try {
      const document =
        mode === "file"
          ? await uploadDocument(courseId, file!)
          : await createNotes(courseId, title.trim(), content);
      setSubmitted(document.filename);
      setFile(null);
      setTitle("");
      setContent("");
    } catch {
      setError(
        mode === "file"
          ? "Upload failed. Supported formats: PDF, DOCX, PPTX, TXT, MD (max 20MB)."
          : "Could not save these notes. Check the title and content, then try again.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="text-2xl font-bold text-navy">Upload</h1>
      <p className="mt-2 text-navy/70">
        Add lecture material as a file (PDF, DOCX, PPTX, TXT, MD) or paste your own typed notes.
        StudyMate extracts the key concepts automatically.
      </p>

      <div className="mt-6">
        <CourseSelect selectedCourseId={courseId} onSelect={setCourseId} />
      </div>

      <div className="mt-6 flex gap-2" role="tablist">
        {(["file", "notes"] as Mode[]).map((option) => (
          <button
            key={option}
            type="button"
            role="tab"
            aria-selected={mode === option}
            onClick={() => {
              setMode(option);
              setError(null);
              setSubmitted(null);
            }}
            className={
              mode === option
                ? "rounded bg-navy px-4 py-1.5 text-sm font-semibold text-gold"
                : "rounded border border-navy/20 px-4 py-1.5 text-sm font-semibold text-navy hover:bg-navy/5"
            }
          >
            {option === "file" ? "Upload a file" : "Type notes"}
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
        {mode === "file" ? (
          <input
            type="file"
            accept={ACCEPTED_EXTENSIONS}
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="rounded border border-navy/20 px-3 py-2"
          />
        ) : (
          <>
            <input
              type="text"
              placeholder="Title (e.g. Week 5 - Normalization)"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={120}
              className="rounded border border-navy/20 px-3 py-2"
            />
            <textarea
              placeholder="Paste or type your lecture notes here..."
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={12}
              className="rounded border border-navy/20 px-3 py-2 font-mono text-sm"
            />
          </>
        )}

        {error && <p className="text-sm text-red-600">{error}</p>}
        {submitted && (
          <p className="text-sm text-green-700">
            Saved {submitted}. Check{" "}
            <Link to="/materials" className="font-semibold text-gold-dark">
              Materials
            </Link>{" "}
            for extracted concepts once processing finishes.
          </p>
        )}

        <button
          type="submit"
          disabled={!canSubmit}
          className="w-fit rounded bg-navy px-4 py-2 font-semibold text-gold hover:bg-navy-light disabled:opacity-50"
        >
          {isSubmitting ? "Saving..." : mode === "file" ? "Upload" : "Save notes"}
        </button>
      </form>
    </div>
  );
}
