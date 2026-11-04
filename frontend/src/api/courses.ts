import { apiClient } from "./client";
import { shrinkImage } from "./schedule";

export interface Course {
  id: string;
  name: string;
  code: string;
  owner_id: string;
  level: number;
  semester: number;
  /** Overview of the material so far; null until something is uploaded. */
  summary: string | null;
  document_count: number;
}

export interface CreateCoursePayload {
  name: string;
  code: string;
  level?: number;
  semester?: number;
}

export async function listCourses(): Promise<Course[]> {
  const { data } = await apiClient.get<Course[]>("/courses");
  return data;
}

export async function getCourse(courseId: string): Promise<Course> {
  const courses = await listCourses();
  const course = courses.find((c) => c.id === courseId);
  if (!course) throw new Error("Course not found");
  return course;
}

export interface CourseProposal {
  code: string;
  name: string;
  /** Null when the document did not say. */
  level: number | null;
  semester: number | null;
  /** Already in My Courses. */
  already_added: boolean;
}

/** Read a photo or PDF of a course list. Nothing is created until addCourses. */
export async function readCourseList(file: File): Promise<CourseProposal[]> {
  const body = await shrinkImage(file);
  const name = body === file ? file.name : file.name.replace(/\.[^.]+$/, "") + ".jpg";
  const form = new FormData();
  form.append("file", body, name);
  const { data } = await apiClient.post<CourseProposal[]>("/courses/read", form, { timeout: 290_000 });
  return data;
}

export async function addCourses(courses: CreateCoursePayload[]): Promise<Course[]> {
  const { data } = await apiClient.post<Course[]>("/courses/bulk", { courses });
  return data;
}

/** Deletes the course with its files, questions, Coach progress and Arcade scores. */
export async function deleteCourse(courseId: string): Promise<void> {
  await apiClient.delete(`/courses/${courseId}`);
}
