import { apiClient } from "./client";

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

export async function uploadDocuments(
  courseId: string,
  files: File[],
): Promise<DocumentSummary[]> {
  const form = new FormData();
  form.append("course_id", courseId);
  for (const file of files) {
    form.append("files", file);
  }
  const { data } = await apiClient.post<DocumentSummary[]>("/documents", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
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
  return data;
}

export async function retryDocument(documentId: string): Promise<DocumentSummary> {
  const { data } = await apiClient.post<DocumentSummary>(`/documents/${documentId}/retry`);
  return data;
}
