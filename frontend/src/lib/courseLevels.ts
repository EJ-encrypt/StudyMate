import { useEffect, useState } from "react";

import { Course, listCourses } from "../api/courses";
import { useAuth } from "../context/AuthContext";

/**
 * The student's courses, shared by My Courses and the sidebar's list of
 * levels, so adding or deleting a course updates both. Earlier levels stay:
 * a level is listed as long as it has a course, plus the student's current
 * level even before it has any.
 */
let courses: Course[] | null = null;
// Whose courses these are, so another account signing in on the same device starts fresh.
let loadedFor: string | null = null;
let loading: Promise<void> | null = null;
const listeners = new Set<(value: Course[] | null) => void>();

export function refreshCourses(): Promise<void> {
  loading ??= listCourses()
    .then((fetched) => {
      courses = fetched;
      listeners.forEach((listener) => listener(courses));
    })
    .catch((error) => {
      // Show an empty list rather than loading forever; the page says why.
      if (courses === null) {
        courses = [];
        listeners.forEach((listener) => listener(courses));
      }
      throw error;
    })
    .finally(() => {
      loading = null;
    });
  return loading;
}

export function levelsOf(list: Course[], current?: number | null): number[] {
  const levels = new Set(list.map((course) => course.level));
  if (current) levels.add(current);
  return [...levels].sort((a, b) => a - b);
}

export function useCourseLevels() {
  const { user } = useAuth();
  const [value, setValue] = useState(courses);

  useEffect(() => {
    listeners.add(setValue);
    if (user && loadedFor !== user.id) {
      loadedFor = user.id;
      courses = null;
      setValue(null);
      refreshCourses().catch(() => undefined);
    }
    return () => {
      listeners.delete(setValue);
    };
  }, [user]);

  const current = user?.level ?? 100;
  return { courses: value, levels: levelsOf(value ?? [], user?.level), current };
}
