import { Camera, ChevronLeft, ChevronRight, ImagePlus, Loader2, X } from "lucide-react";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import { errorMessage } from "../api/client";
import { uploadDocuments } from "../api/documents";
import { photosToPdf } from "../lib/photoPdf";
import { Alert } from "./ui";

const MAX_PAGES = 20;

interface Page {
  id: string;
  file: File;
  preview: string;
}

/**
 * Notes written in an exercise book: photograph each page, put them in order,
 * and they go up as one document that StudyMate reads like any other.
 */
export default function PhotoNotes({ courseId, onUploaded }: { courseId: string; onUploaded: () => Promise<void> }) {
  const [title, setTitle] = useState("");
  const [pages, setPages] = useState<Page[]>([]);
  const [isBusy, setIsBusy] = useState(false);
  const [progress, setProgress] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const camera = useRef<HTMLInputElement>(null);
  const gallery = useRef<HTMLInputElement>(null);

  // Previews are object URLs; let them go when the pages do.
  const previews = useMemo(() => pages.map((page) => page.preview), [pages]);
  const latest = useRef(previews);
  latest.current = previews;
  useEffect(() => () => latest.current.forEach((url) => URL.revokeObjectURL(url)), []);

  function add(selected: FileList | null, input: HTMLInputElement | null) {
    setError(null);
    setNotice(null);
    const images = Array.from(selected ?? []).filter((file) => file.type.startsWith("image/") || /\.(heic|heif)$/i.test(file.name));
    if (input) input.value = "";
    if (images.length === 0) return;
    const room = MAX_PAGES - pages.length;
    if (images.length > room) setError(`Up to ${MAX_PAGES} pages at a time. Save these, then add the rest as another set.`);
    const added = images.slice(0, Math.max(0, room)).map((file) => ({
      id: `${file.name}-${file.lastModified}-${Math.random().toString(36).slice(2)}`,
      file,
      preview: URL.createObjectURL(file),
    }));
    setPages((current) => [...current, ...added]);
  }

  function remove(id: string) {
    setPages((current) => {
      const page = current.find((p) => p.id === id);
      if (page) URL.revokeObjectURL(page.preview);
      return current.filter((p) => p.id !== id);
    });
  }

  function move(index: number, step: -1 | 1) {
    setPages((current) => {
      const target = index + step;
      if (target < 0 || target >= current.length) return current;
      const next = [...current];
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    if (pages.length === 0) return;
    setIsBusy(true);
    setError(null);
    setNotice(null);
    try {
      setProgress(`Preparing ${pages.length} page${pages.length === 1 ? "" : "s"}...`);
      const pdf = await photosToPdf(
        pages.map((page) => page.file),
        title,
      );
      setProgress("Uploading...");
      await uploadDocuments(courseId, [pdf]);
      pages.forEach((page) => URL.revokeObjectURL(page.preview));
      setPages([]);
      setTitle("");
      setNotice("Photos saved. StudyMate is reading your handwriting now; this takes a minute or two.");
      await onUploaded();
    } catch (err) {
      setError(errorMessage(err, "Could not upload those photos. Please try again."));
    } finally {
      setIsBusy(false);
      setProgress(null);
    }
  }

  return (
    <form onSubmit={save} className="flex flex-col gap-3">
      <input
        type="text"
        placeholder="Title, e.g. Week 5 - Normalization"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        maxLength={80}
        className="input"
      />

      <div className="grid grid-cols-2 gap-2 sm:flex">
        <button type="button" onClick={() => camera.current?.click()} disabled={isBusy} className="btn-secondary">
          <Camera className="h-4 w-4" aria-hidden /> Take photo
        </button>
        <button type="button" onClick={() => gallery.current?.click()} disabled={isBusy} className="btn-secondary">
          <ImagePlus className="h-4 w-4" aria-hidden /> From gallery
        </button>
        {/* capture opens the back camera straight away on phones; a computer falls back to a file picker. */}
        <input
          ref={camera}
          type="file"
          accept="image/*"
          capture="environment"
          onChange={(e) => add(e.target.files, e.target)}
          className="sr-only"
          aria-label="Take a photo of a page"
          tabIndex={-1}
        />
        <input
          ref={gallery}
          type="file"
          accept="image/*"
          multiple
          onChange={(e) => add(e.target.files, e.target)}
          className="sr-only"
          aria-label="Choose photos of pages"
          tabIndex={-1}
        />
      </div>

      {pages.length === 0 ? (
        <p className="rounded-xl border-2 border-dashed border-ink/15 px-4 py-6 text-center text-sm text-ink/55">
          Photograph each page of your notes in order, in good light and with the whole page in the frame.
        </p>
      ) : (
        <ol className="grid grid-cols-3 gap-2 sm:grid-cols-5">
          {pages.map((page, index) => (
            <li key={page.id} className="relative overflow-hidden rounded-lg border border-ink/10 bg-ink/5">
              <img src={page.preview} alt={`Page ${index + 1}`} className="aspect-[3/4] w-full object-cover" />
              <span className="absolute left-1 top-1 rounded bg-navy/85 px-1.5 text-xs font-bold text-white">
                {index + 1}
              </span>
              <button
                type="button"
                onClick={() => remove(page.id)}
                aria-label={`Remove page ${index + 1}`}
                className="absolute right-1 top-1 flex h-7 w-7 items-center justify-center rounded-full bg-navy/85 text-white"
              >
                <X className="h-4 w-4" aria-hidden />
              </button>
              {pages.length > 1 && (
                <div className="absolute inset-x-1 bottom-1 flex justify-between">
                  <button
                    type="button"
                    onClick={() => move(index, -1)}
                    disabled={index === 0}
                    aria-label={`Move page ${index + 1} earlier`}
                    className="flex h-7 w-7 items-center justify-center rounded-full bg-navy/85 text-white disabled:invisible"
                  >
                    <ChevronLeft className="h-4 w-4" aria-hidden />
                  </button>
                  <button
                    type="button"
                    onClick={() => move(index, 1)}
                    disabled={index === pages.length - 1}
                    aria-label={`Move page ${index + 1} later`}
                    className="flex h-7 w-7 items-center justify-center rounded-full bg-navy/85 text-white disabled:invisible"
                  >
                    <ChevronRight className="h-4 w-4" aria-hidden />
                  </button>
                </div>
              )}
            </li>
          ))}
        </ol>
      )}

      {error && <Alert>{error}</Alert>}
      {notice && <Alert kind="success">{notice}</Alert>}

      <button type="submit" disabled={isBusy || pages.length === 0} className="btn-primary w-fit">
        {isBusy && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
        {isBusy
          ? progress
          : pages.length > 0
            ? `Save ${pages.length} page${pages.length === 1 ? "" : "s"}`
            : "Save photos"}
      </button>
    </form>
  );
}
