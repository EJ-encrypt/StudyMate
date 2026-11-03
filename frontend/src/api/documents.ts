import { apiClient } from "./client";
import { runMyJobs } from "./jobs";
import { STORAGE_BUCKET, supabase } from "../lib/supabase";

export type DocumentStatus = "pending" | "processing" | "completed" | "failed";

export interface DocumentSummary {
  id: string;
  course_id: string;
  filename: string;
  status: DocumentStatus;
  error_message: string | null;
  /** True when the failure was transient, so retrying is worth offering. */
  can_retry: boolean;
  created_at: string;
}

export interface Concept {
  id: string;
  name: string;
  summary: string;
}

export interface DocumentDetail extends DocumentSummary {
  concepts: Concept[];
}

export async function listDocuments(courseId: string): Promise<DocumentSummary[]> {
  const { data } = await apiClient.get<DocumentSummary[]>("/documents", {
    params: { course_id: courseId },
  });
  return data;
}

export async function getDocument(documentId: string): Promise<DocumentDetail> {
  const { data } = await apiClient.get<DocumentDetail>(`/documents/${documentId}`);
  return data;
}

interface UploadTarget {
  document_id: string;
  filename: string;
  original_filename: string;
  method: "supabase" | "local";
  path: string;
  token: string;
  url: string;
}

/**
 * Upload straight to storage, then tell the API.
 *
 * Files do not pass through the API: Vercel rejects request bodies over
 * 4.5MB, and lecture slides are often bigger. The API hands out a signed URL
 * per file, the browser sends the bytes there, and only then are the
 * documents recorded and queued for reading.
 */
export async function uploadDocuments(
  courseId: string,
  files: File[],
  onProgress?: (done: number, total: number) => void,
): Promise<DocumentSummary[]> {
  const { data: targets } = await apiClient.post<UploadTarget[]>("/documents/uploads", {
    course_id: courseId,
    files: files.map((file) => ({ filename: file.name, size: file.size })),
  });

  let done = 0;
  await Promise.all(
    targets.map(async (target, index) => {
      const file = files[index];
      if (target.method === "supabase") {
        if (!supabase) throw new Error("Storage is not configured");
        const { error } = await supabase.storage
          .from(STORAGE_BUCKET)
          .uploadToSignedUrl(target.path, target.token, file, {
            contentType: file.type || "application/octet-stream",
          });
        if (error) throw error;
      } else {
        await apiClient.put(target.url, file, {
          headers: { "Content-Type": "application/octet-stream" },
        });
      }
      done += 1;
      onProgress?.(done, files.length);
    }),
  );

  const { data } = await apiClient.post<DocumentSummary[]>("/documents/complete", {
    course_id: courseId,
    uploads: targets.map((t) => ({ document_id: t.document_id, filename: t.filename })),
  });
  runMyJobs();
  return data;
}

export async function createNotes(
  courseId: string,
  title: string,
  content: string,
): Promise<DocumentSummary> {
  const { data } = await apiClient.post<DocumentSummary>("/documents/notes", {
    course_id: courseId,
    title,
    content,
  });
  runMyJobs();
  return data;
}

export async function retryDocument(documentId: string): Promise<DocumentSummary> {
  const { data } = await apiClient.post<DocumentSummary>(`/documents/${documentId}/retry`);
  runMyJobs();
  return data;
}
