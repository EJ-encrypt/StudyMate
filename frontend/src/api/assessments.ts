import { apiClient } from "./client";

export type ItemKind = "flashcard" | "mcq" | "fill_blank";
export type AssessmentStatus = "pending" | "processing" | "completed" | "failed";

export interface AssessmentSummary {
  id: string;
  course_id: string;
  document_id: string;
  title: string;
  kind: ItemKind;
  status: AssessmentStatus;
  error_message: string | null;
  created_at: string;
}

export interface AssessmentItem {
  id: string;
  position: number;
  kind: ItemKind;
  question: string;
  options: string[];
  /** Present for flashcards only; graded kinds withhold it until an attempt. */
  answer: string | null;
  explanation: string | null;
}

export interface AssessmentDetail extends AssessmentSummary {
  items: AssessmentItem[];
}

export interface GradedAnswer {
  item_id: string;
  response: string;
  is_correct: boolean;
  correct_answer: string;
  explanation: string;
}

export interface AttemptResult {
  id: string;
  assessment_id: string;
  correct_count: number;
  total_count: number;
  answers: GradedAnswer[];
}

export const KIND_LABELS: Record<ItemKind, string> = {
  flashcard: "Flashcards",
  mcq: "Multiple choice",
  fill_blank: "Fill in the blank",
};

export async function createAssessment(
  documentId: string,
  kind: ItemKind,
  count = 10,
): Promise<AssessmentSummary> {
  const { data } = await apiClient.post<AssessmentSummary>("/assessments", {
    document_id: documentId,
    kind,
    count,
  });
  return data;
}

export async function listAssessments(courseId: string): Promise<AssessmentSummary[]> {
  const { data } = await apiClient.get<AssessmentSummary[]>("/assessments", {
    params: { course_id: courseId },
  });
  return data;
}

export async function getAssessment(assessmentId: string): Promise<AssessmentDetail> {
  const { data } = await apiClient.get<AssessmentDetail>(`/assessments/${assessmentId}`);
  return data;
}

export async function submitAttempt(
  assessmentId: string,
  answers: { item_id: string; response: string }[],
): Promise<AttemptResult> {
  const { data } = await apiClient.post<AttemptResult>(`/assessments/${assessmentId}/attempts`, {
    answers,
  });
  return data;
}
