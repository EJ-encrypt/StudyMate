import { BookOpen } from "lucide-react";
import { useEffect, useState } from "react";

import { Course, listCourses } from "../api/courses";
import { useAuth } from "../context/AuthContext";
import { coursesIn, startingTerm, Term } from "../lib/term";
import TermPicker from "./TermPicker";

interface CourseSelectProps {
  selectedCourseId: string | null;
  onSelect: (courseId: string) => void;
}

/**
 * Level, semester, then course. Starts on the term last chosen (or the
 * student's current one), so revising an earlier year is two taps away.
 */
export default function CourseSelect({ selectedCourseId, onSelect }: CourseSelectProps) {
  const { user } = useAuth();
  const [courses, setCourses] = useState<Course[]>([]);
  const [term, setTerm] = useState<Term | null>(null);

  useEffect(() => {
    listCourses().then((fetched) => {
      setCourses(fetched);
      const start = startingTerm(fetched, { level: user?.level ?? undefined, semester: user?.semester ?? undefined }, selectedCourseId);
      setTerm(start);
      const inTerm = coursesIn(fetched, start);
      if (!inTerm.some((course) => course.id === selectedCourseId) && inTerm.length > 0) onSelect(inTerm[0].id);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const shown = coursesIn(courses, term);

  function changeTerm(next: Term) {
    setTerm(next);
    const first = coursesIn(courses, next)[0];
    if (first) onSelect(first.id);
  }

  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
      <TermPicker courses={courses} term={term} onChange={changeTerm} />
      <label className="relative flex min-w-0 flex-1 items-center sm:max-w-sm">
        <span className="sr-only">Course</span>
        <BookOpen className="pointer-events-none absolute left-3 h-4 w-4 text-ink/40" aria-hidden />
        <select value={selectedCourseId ?? ""} onChange={(e) => onSelect(e.target.value)} className="input pl-9 font-medium">
          {shown.length === 0 && <option value="">No courses yet</option>}
          {shown.map((course) => (
            <option key={course.id} value={course.id}>
              {course.code} - {course.name}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
