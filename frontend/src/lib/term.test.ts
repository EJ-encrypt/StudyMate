import { beforeEach, describe, expect, it } from "vitest";

import { Course } from "../api/courses";
import { coursesIn, rememberTerm, startingTerm, termsOf } from "./term";

function course(id: string, level: number, semester: number): Course {
  return { id, name: id, code: id, owner_id: "me", level, semester, summary: null, document_count: 1 };
}

const courses = [course("a", 100, 1), course("b", 100, 2), course("c", 200, 1), course("d", 200, 1)];

describe("terms", () => {
  beforeEach(() => localStorage.clear());

  it("lists each level and semester that has courses, in order", () => {
    expect(termsOf(courses)).toEqual([
      { level: 100, semester: 1 },
      { level: 100, semester: 2 },
      { level: 200, semester: 1 },
    ]);
    expect(coursesIn(courses, { level: 200, semester: 1 }).map((c) => c.id)).toEqual(["c", "d"]);
  });

  it("starts on the student's current term, so a new level is the default", () => {
    expect(startingTerm(courses, { level: 200, semester: 1 })).toEqual({ level: 200, semester: 1 });
  });

  it("remembers going back to an earlier level", () => {
    rememberTerm({ level: 100, semester: 2 });
    expect(startingTerm(courses, { level: 200, semester: 1 })).toEqual({ level: 100, semester: 2 });
  });

  it("follows a course the page asks for, and falls back to the latest term with courses", () => {
    rememberTerm({ level: 200, semester: 1 });
    expect(startingTerm(courses, {}, "a")).toEqual({ level: 100, semester: 1 });
    localStorage.clear();
    expect(startingTerm(courses, { level: 400, semester: 2 })).toEqual({ level: 200, semester: 1 });
    expect(startingTerm([], { level: 100, semester: 1 })).toBeNull();
  });
});
