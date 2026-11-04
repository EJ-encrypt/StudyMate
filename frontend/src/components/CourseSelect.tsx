import { BookOpen, Plus } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { Course, createCourse, listCourses } from "../api/courses";

interface CourseSelectProps {
  selectedCourseId: string | null;
  onSelect: (courseId: string) => void;
  /** Hide the inline "new course" form where creating one makes no sense. */
  allowCreate?: boolean;
}

export default function CourseSelect({ selectedCourseId, onSelect, allowCreate = true }: CourseSelectProps) {
  const [courses, setCourses] = useState<Course[]>([]);
  const [isCreating, setIsCreating] = useState(false);
  const [name, setName] = useState("");
  const [code, setCode] = useState("");

  useEffect(() => {
    listCourses().then((fetched) => {
      setCourses(fetched);
      if (!selectedCourseId && fetched.length > 0) {
        onSelect(fetched[0].id);
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    const course = await createCourse({ name, code });
    setCourses((prev) => [...prev, course]);
    onSelect(course.id);
    setIsCreating(false);
    setName("");
    setCode("");
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <label className="relative flex min-w-0 flex-1 items-center sm:max-w-sm">
        <span className="sr-only">Course</span>
        <BookOpen className="pointer-events-none absolute left-3 h-4 w-4 text-ink/40" aria-hidden />
        <select
          value={selectedCourseId ?? ""}
          onChange={(e) => onSelect(e.target.value)}
          className="input pl-9 font-medium"
        >
          {courses.length === 0 && <option value="">No courses yet</option>}
          {courses.map((course) => (
            <option key={course.id} value={course.id}>
              {course.code} - {course.name}
            </option>
          ))}
        </select>
      </label>
      {allowCreate && (
        <button type="button" onClick={() => setIsCreating((prev) => !prev)} className="btn-ghost text-gold-dark">
          <Plus className="h-4 w-4" aria-hidden /> New course
        </button>
      )}
      {isCreating && (
        <form onSubmit={handleCreate} className="flex w-full flex-wrap items-center gap-2">
          <input
            type="text"
            placeholder="Code (e.g. CS201)"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            required
            className="input w-36"
          />
          <input
            type="text"
            placeholder="Course name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            className="input w-56"
          />
          <button type="submit" className="btn-primary">
            Create
          </button>
        </form>
      )}
    </div>
  );
}
