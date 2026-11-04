import { Course } from "../api/courses";
import { rememberTerm, Term, termsOf } from "../lib/term";

/** Level, then semester: only the ones that have courses. */
export default function TermPicker({
  courses,
  term,
  onChange,
}: {
  courses: Course[];
  term: Term | null;
  onChange: (term: Term) => void;
}) {
  const terms = termsOf(courses);
  if (!term || terms.length === 0) return null;
  const levels = [...new Set(terms.map((t) => t.level))];
  const semesters = terms.filter((t) => t.level === term.level).map((t) => t.semester);

  function choose(next: Term) {
    rememberTerm(next);
    onChange(next);
  }

  return (
    <div className="flex gap-2" data-tour="term-picker">
      <label className="min-w-0 flex-1 sm:w-32 sm:flex-none">
        <span className="sr-only">Level</span>
        <select
          value={term.level}
          onChange={(e) => {
            const level = Number(e.target.value);
            const available = terms.filter((t) => t.level === level).map((t) => t.semester);
            choose({ level, semester: available.includes(term.semester) ? term.semester : available[0] });
          }}
          className="input font-medium"
        >
          {levels.map((level) => (
            <option key={level} value={level}>
              Level {level}
            </option>
          ))}
        </select>
      </label>
      <label className="min-w-0 flex-1 sm:w-36 sm:flex-none">
        <span className="sr-only">Semester</span>
        <select
          value={term.semester}
          onChange={(e) => choose({ level: term.level, semester: Number(e.target.value) })}
          className="input font-medium"
        >
          {semesters.map((semester) => (
            <option key={semester} value={semester}>
              Semester {semester}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
