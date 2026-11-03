import { apiClient } from "./client";
import { runMyJobs } from "./jobs";

export type ItemKind = "flashcard" | "mcq" | "fill_blank" | "short_answer";
export type AssessmentKind = ItemKind | "exam";
export type AssessmentStatus = "pending" | "processing" | "completed" | "failed";

export interface AssessmentSummary {
  id: string;
  course_id: string;
  document_id: string;
  title: string;
  kind: AssessmentKind;
  status: AssessmentStatus;
  error_message: string | null;
  can_retry: boolean;
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

export interface NewBadge {
  code: string;
  name: string;
  description: string;
}

export interface AttemptResult {
  id: string;
  assessment_id: string;
  correct_count: number;
  total_count: number;
  answers: GradedAnswer[];
  new_badges: NewBadge[];
}

export const KIND_LABELS: Record<AssessmentKind, string> = {
  flashcard: "Flashcards",
  mcq: "Multiple choice",
  fill_blank: "Fill in the blank",
  short_answer: "Short answer",
  exam: "Exam paper",
};

export async function createAssessment(
  documentId: string,
  kind: AssessmentKind,
  count = 10,
): Promise<AssessmentSummary> {
  const { data } = await apiClient.post<AssessmentSummary>("/assessments", {
    document_id: documentId,
    kind,
    count,
  });
  runMyJobs();
  return data;
}

/** Draws on the whole course knowledge base rather than one document. */
export async function createCumulativeAssessment(
  courseId: string,
  kind: AssessmentKind,
  count = 10,
): Promise<AssessmentSummary> {
  const { data } = await apiClient.post<AssessmentSummary>("/assessments", {
    course_id: courseId,
    kind,
    count,
  });
  runMyJobs();
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

export async function retryAssessment(assessmentId: string): Promise<AssessmentSummary> {
  const { data } = await apiClient.post<AssessmentSummary>(`/assessments/${assessmentId}/retry`);
  runMyJobs();
  return data;
}
