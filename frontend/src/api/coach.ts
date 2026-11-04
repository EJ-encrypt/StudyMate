import { apiClient } from "./client";

export type ConceptStatus = "strong" | "developing" | "weak" | "unpractised";

export interface ConceptProgress {
  concept_id: string;
  name: string;
  summary: string;
  /** Null until the concept has been answered at least once. */
  score: number | null;
  attempts: number;
  correct: number;
  status: ConceptStatus;
  last_seen_at: string | null;
}

export interface CoachSummary {
  course_id: string;
  concept_count: number;
  overall_mastery: number | null;
  strong: number;
  developing: number;
  weak: number;
  unpractised: number;
  recommendations: ConceptProgress[];
  /** At most five groups of related concepts to revise together. */
  topics: RevisionTopic[];
  /** Concepts needing work beyond those grouped into topics. */
  more_to_revise: number;
  concepts: ConceptProgress[];
}

export interface RevisionTopic {
  /** Named after its most central concept. */
  title: string;
  summary: string;
  status: ConceptStatus;
  concepts: ConceptProgress[];
}

export const STATUS_LABELS: Record<ConceptStatus, string> = {
  strong: "Strong",
  developing: "Developing",
  weak: "Needs work",
  unpractised: "Not practised",
};

export const STATUS_STYLES: Record<ConceptStatus, string> = {
  strong: "bg-green-100 text-green-800",
  developing: "bg-gold/25 text-ink",
  weak: "bg-red-100 text-red-700",
  unpractised: "bg-ink/10 text-ink/70",
};

export async function getCoachSummary(courseId: string): Promise<CoachSummary> {
  const { data } = await apiClient.get<CoachSummary>(`/coach/${courseId}`);
  return data;
}

export interface ConceptSource {
  document_id: string;
  filename: string;
}

export interface ConceptDetail {
  concept_id: string;
  course_id: string;
  name: string;
  summary: string;
  score: number | null;
  attempts: number;
  correct: number;
  status: ConceptStatus;
  last_seen_at: string | null;
  sources: ConceptSource[];
  mentions: string[];
}

export async function getConceptDetail(conceptId: string): Promise<ConceptDetail> {
  const { data } = await apiClient.get<ConceptDetail>(`/coach/concept/${conceptId}`);
  return data;
}
