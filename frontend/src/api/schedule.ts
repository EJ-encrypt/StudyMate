import { apiClient } from "./client";
import { NewBadge } from "./assessments";

export interface LectureSlot {
  id: string;
  title: string;
  course_id: string | null;
  course_code: string | null;
  /** 0 = Monday ... 6 = Sunday. */
  day_of_week: number;
  /** "HH:MM:SS" in the student's own time zone. */
  start_time: string;
  end_time: string;
  venue: string;
}

export interface SlotInput {
  title: string;
  course_id: string | null;
  day_of_week: number;
  start_time: string;
  end_time: string;
  venue: string;
}

export interface SlotProposal extends SlotInput {
  course_code: string;
}

export const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
export const SHORT_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

/** "09:00:00" -> "09:00" */
export function hhmm(value: string): string {
  return value.slice(0, 5);
}

/** Today as 0 = Monday ... 6 = Sunday, matching the API. */
export function todayIndex(): number {
  return (new Date().getDay() + 6) % 7;
}

export async function listSlots(): Promise<LectureSlot[]> {
  const { data } = await apiClient.get<LectureSlot[]>("/schedule");
  return data;
}

export async function getSlot(slotId: string): Promise<LectureSlot> {
  const { data } = await apiClient.get<LectureSlot>(`/schedule/${slotId}`);
  return data;
}

export async function createSlot(slot: SlotInput): Promise<LectureSlot> {
  const { data } = await apiClient.post<LectureSlot>("/schedule", slot);
  return data;
}

export async function createSlots(slots: SlotInput[], replace = false): Promise<LectureSlot[]> {
  const { data } = await apiClient.post<LectureSlot[]>("/schedule/bulk", { slots, replace });
  return data;
}

export async function updateSlot(slotId: string, slot: Partial<SlotInput>): Promise<LectureSlot> {
  const { data } = await apiClient.patch<LectureSlot>(`/schedule/${slotId}`, slot);
  return data;
}

export async function deleteSlot(slotId: string): Promise<void> {
  await apiClient.delete(`/schedule/${slotId}`);
}

/**
 * Shrink a phone photo before sending it: the API accepts at most 4MB, and
 * the AI reads a 2000px image as well as a 4000px one.
 */
async function shrinkImage(file: File): Promise<Blob> {
  if (!file.type.startsWith("image/") || file.size < 1.5 * 1024 * 1024) return file;
  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, 2000 / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  canvas.getContext("2d")!.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  return new Promise((resolve) => canvas.toBlob((blob) => resolve(blob ?? file), "image/jpeg", 0.85));
}

export async function readTimetable(file: File): Promise<SlotProposal[]> {
  const body = await shrinkImage(file);
  const name = body === file ? file.name : file.name.replace(/\.[^.]+$/, "") + ".jpg";
  const form = new FormData();
  form.append("file", body, name);
  const { data } = await apiClient.post<SlotProposal[]>("/schedule/read", form, { timeout: 290_000 });
  return data;
}

export interface ReflectionResult {
  document_id: string;
  course_id: string;
  new_badges: NewBadge[];
}

export async function addReflection(
  slotId: string,
  content: string,
  courseId: string | null,
): Promise<ReflectionResult> {
  const { data } = await apiClient.post<ReflectionResult>(`/schedule/${slotId}/reflection`, {
    content,
    course_id: courseId,
  });
  return data;
}
