import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";

import { uploadDocument } from "../api/documents";
import CourseSelect from "../components/CourseSelect";

export default function Upload() {
  const [courseId, setCourseId] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadedFilename, setUploadedFilename] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!courseId || !file) return;

    setIsUploading(true);
    setError(null);
    setUploadedFilename(null);
    try {
      const document = await uploadDocument(courseId, file);
      setUploadedFilename(document.filename);
      setFile(null);
    } catch {
      setError("Upload failed. Only PDF files up to 20MB are supported right now.");
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="text-2xl font-bold text-navy">Upload</h1>
      <p className="mt-2 text-navy/70">
        Upload a PDF of your lecture material. StudyMate extracts key concepts automatically.
      </p>

      <div className="mt-6">
        <CourseSelect selectedCourseId={courseId} onSelect={setCourseId} />
      </div>

      <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
        <input
          type="file"
          accept="application/pdf"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="rounded border border-navy/20 px-3 py-2"
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        {uploadedFilename && (
          <p className="text-sm text-green-700">
            Uploaded {uploadedFilename}. Check{" "}
            <Link to="/materials" className="font-semibold text-gold-dark">
              Materials
            </Link>{" "}
            for extracted concepts once processing finishes.
          </p>
        )}
        <button
          type="submit"
          disabled={!courseId || !file || isUploading}
          className="w-fit rounded bg-navy px-4 py-2 font-semibold text-gold hover:bg-navy-light disabled:opacity-50"
        >
          {isUploading ? "Uploading..." : "Upload"}
        </button>
      </form>
    </div>
  );
}
