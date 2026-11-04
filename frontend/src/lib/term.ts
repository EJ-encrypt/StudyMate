import { Course } from "../api/courses";

/**
 * A level and semester, e.g. Level 200 Semester 1. The Study Engine, Coach
 * and Arcade pick one before a course, so earlier years stay easy to revise.
 */
export interface Term {
  level: number;
  semester: number;
}

const STORAGE_KEY = "studymate-term";

export function sameTerm(a: Term | null, b: Term | null): boolean {
  return !!a && !!b && a.level === b.level && a.semester === b.semester;
}

/** Every term that has a course, in order. */
export function termsOf(courses: Course[]): Term[] {
  const seen = new Map<string, Term>();
  for (const { level, semester } of courses) seen.set(`${level}-${semester}`, { level, semester });
  return [...seen.values()].sort((a, b) => a.level - b.level || a.semester - b.semester);
}

export function coursesIn(courses: Course[], term: Term | null): Course[] {
  return term ? courses.filter((course) => course.level === term.level && course.semester === term.semester) : courses;
}

function remembered(): Term | null {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null");
    return saved && typeof saved.level === "number" && typeof saved.semester === "number" ? saved : null;
  } catch {
    return null;
  }
}

export function rememberTerm(term: Term) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(term));
  } catch {
    // Private browsing: the choice just is not remembered.
  }
}

/**
 * Where to start: the term of a course asked for by the page, else the last
 * term chosen, else the student's current one, else the latest with courses.
 */
export function startingTerm(courses: Course[], current: Partial<Term>, courseId?: string | null): Term | null {
  const terms = termsOf(courses);
  if (terms.length === 0) return null;
  const asked = courseId ? courses.find((course) => course.id === courseId) : undefined;
  const candidates: (Term | null)[] = [
    asked ? { level: asked.level, semester: asked.semester } : null,
    remembered(),
    current.level && current.semester ? { level: current.level, semester: current.semester } : null,
  ];
  return candidates.find((candidate) => terms.some((term) => sameTerm(term, candidate))) ?? terms[terms.length - 1];
}
