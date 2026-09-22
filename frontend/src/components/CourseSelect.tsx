import { FormEvent, useEffect, useState } from "react";

import { Course, createCourse, listCourses } from "../api/courses";

interface CourseSelectProps {
  selectedCourseId: string | null;
  onSelect: (courseId: string) => void;
}

export default function CourseSelect({ selectedCourseId, onSelect }: CourseSelectProps) {
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
    <div className="flex flex-wrap items-center gap-3">
      <label className="text-sm font-semibold text-navy">Course</label>
      <select
        value={selectedCourseId ?? ""}
        onChange={(e) => onSelect(e.target.value)}
        className="rounded border border-navy/20 px-3 py-1.5"
      >
        {courses.length === 0 && <option value="">No courses yet</option>}
        {courses.map((course) => (
          <option key={course.id} value={course.id}>
            {course.code} - {course.name}
          </option>
        ))}
      </select>
      <button
        type="button"
        onClick={() => setIsCreating((prev) => !prev)}
        className="text-sm font-semibold text-gold-dark hover:underline"
      >
        + New course
      </button>
      {isCreating && (
        <form onSubmit={handleCreate} className="flex flex-wrap items-center gap-2">
          <input
            type="text"
            placeholder="Code (e.g. CS201)"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            required
            className="w-32 rounded border border-navy/20 px-2 py-1 text-sm"
          />
          <input
            type="text"
            placeholder="Course name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            className="w-48 rounded border border-navy/20 px-2 py-1 text-sm"
          />
          <button type="submit" className="rounded bg-navy px-3 py-1 text-sm font-semibold text-gold">
            Create
          </button>
        </form>
      )}
    </div>
  );
}
