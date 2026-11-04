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

/** Groups courses into L100 Sem 1, L100 Sem 2, L200 ... in study order. */
export function groupByLevelAndSemester(courses: Course[]): {
  key: string;
  label: string;
  courses: Course[];
}[] {
  const groups = new Map<string, { key: string; label: string; courses: Course[] }>();
  for (const course of courses) {
    const key = `${course.level}-${course.semester}`;
    if (!groups.has(key)) {
      groups.set(key, {
        key,
        label: `Level ${course.level} · Semester ${course.semester}`,
        courses: [],
      });
    }
    groups.get(key)!.courses.push(course);
  }
  return [...groups.values()].sort((a, b) => a.key.localeCompare(b.key, undefined, { numeric: true }));
}

export async function listCourses(): Promise<Course[]> {
  const { data } = await apiClient.get<Course[]>("/courses");
  return data;
}

export async function createCourse(payload: CreateCoursePayload): Promise<Course> {
  const { data } = await apiClient.post<Course>("/courses", payload);
  return data;
}

export interface CourseConcept {
  id: string;
  name: string;
  summary: string;
  document_count: number;
}

export async function listCourseConcepts(courseId: string): Promise<CourseConcept[]> {
  const { data } = await apiClient.get<CourseConcept[]>(`/courses/${courseId}/concepts`);
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
