import { apiClient } from "./client";

export interface Course {
  id: string;
  name: string;
  code: string;
  owner_id: string;
}

export interface CreateCoursePayload {
  name: string;
  code: string;
}

export async function listCourses(): Promise<Course[]> {
  const { data } = await apiClient.get<Course[]>("/courses");
  return data;
}

export async function createCourse(payload: CreateCoursePayload): Promise<Course> {
  const { data } = await apiClient.post<Course>("/courses", payload);
  return data;
}
