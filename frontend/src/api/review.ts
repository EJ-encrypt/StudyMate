import { AssessmentItem } from "./assessments";
import { apiClient } from "./client";

/** Cards seen before and due for another look, answers included. */
export async function getDueCards(courseId?: string): Promise<AssessmentItem[]> {
  const { data } = await apiClient.get<{ items: AssessmentItem[] }>("/flashcards/due", {
    params: courseId ? { course_id: courseId } : undefined,
  });
  return data.items;
}

export interface CourseDue {
  course_id: string;
  code: string;
  name: string;
  due: number;
}

export async function getDueByCourse(): Promise<CourseDue[]> {
  const { data } = await apiClient.get<CourseDue[]>("/flashcards/due/courses");
  return data;
}

export interface ReviewResult {
  item_id: string;
  /** 1 (still learning) to 5 (well known). */
  box: number;
  due_at: string;
}

export async function reviewCard(itemId: string, remembered: boolean): Promise<ReviewResult> {
  const { data } = await apiClient.post<ReviewResult>(`/flashcards/${itemId}/review`, { remembered });
  return data;
}
