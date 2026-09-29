import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Course, createCourse, groupByLevelAndSemester, listCourses } from "../api/courses";
import PageHeader from "../components/PageHeader";
import { useAuth } from "../context/AuthContext";

const LEVELS = [100, 200, 300, 400, 500, 600];

export default function MyCourses() {
  const { user } = useAuth();
  const [courses, setCourses] = useState<Course[]>([]);
  const [isAdding, setIsAdding] = useState(false);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [level, setLevel] = useState(user?.level ?? 100);
  const [semester, setSemester] = useState(user?.semester ?? 1);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listCourses()
      .then(setCourses)
      .catch(() => setError("Could not load your courses."));
  }, []);

  async function handleAdd(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await createCourse({ name, code, level, semester });
      setCourses(await listCourses());
      setCode("");
      setName("");
      setIsAdding(false);
    } catch {
      setError("Could not add that course.");
    }
  }

  const groups = groupByLevelAndSemester(courses);

  return (
    <>
      <PageHeader
        title="My Courses"
        subtitle={user?.school ?? undefined}
        actions={
          <button
            type="button"
            onClick={() => setIsAdding((prev) => !prev)}
            className="rounded bg-navy px-3 py-1.5 text-sm font-semibold text-gold hover:bg-navy-light"
          >
            {isAdding ? "Cancel" : "Add course"}
          </button>
        }
      />

      {isAdding && (
        <form
          onSubmit={handleAdd}
          className="mb-4 flex flex-wrap items-end gap-2 rounded border border-navy/15 bg-white p-3"
        >
          <label className="text-xs font-semibold text-navy">
            Code
            <input
              required
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="CS302"
              className="mt-1 block w-28 rounded border border-navy/20 px-2 py-1 text-sm font-normal"
            />
          </label>
          <label className="text-xs font-semibold text-navy">
            Course name
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Database Systems"
              className="mt-1 block w-56 rounded border border-navy/20 px-2 py-1 text-sm font-normal"
            />
          </label>
          <label className="text-xs font-semibold text-navy">
            Level
            <select
              value={level}
              onChange={(e) => setLevel(Number(e.target.value))}
              className="mt-1 block rounded border border-navy/20 px-2 py-1 text-sm font-normal"
            >
              {LEVELS.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs font-semibold text-navy">
            Semester
            <select
              value={semester}
              onChange={(e) => setSemester(Number(e.target.value))}
              className="mt-1 block rounded border border-navy/20 px-2 py-1 text-sm font-normal"
            >
              <option value={1}>1</option>
              <option value={2}>2</option>
            </select>
          </label>
          <button
            type="submit"
            className="rounded bg-navy px-3 py-1.5 text-sm font-semibold text-gold hover:bg-navy-light"
          >
            Save
          </button>
        </form>
      )}

      {error && <p className="mb-3 text-sm text-red-600">{error}</p>}

      {courses.length === 0 && !isAdding && (
        <p className="text-sm text-navy/60">
          No courses yet. Add your first one to start uploading material.
        </p>
      )}

      {groups.map((group) => (
        <section key={group.key} className="mb-5">
          <h2 className="mb-2 text-xs font-bold uppercase tracking-wide text-navy/50">
            {group.label}
          </h2>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {group.courses.map((course) => (
              <Link
                key={course.id}
                to={`/courses/${course.id}`}
                className="rounded border border-navy/15 bg-white p-3 hover:border-gold hover:shadow-sm"
              >
                <p className="text-sm font-bold text-navy">{course.code}</p>
                <p className="text-sm text-navy/75">{course.name}</p>
                <p className="mt-1 text-xs text-navy/50">
                  {course.document_count === 0
                    ? "No material yet"
                    : `${course.document_count} file${course.document_count === 1 ? "" : "s"}`}
                </p>
              </Link>
            ))}
          </div>
        </section>
      ))}
    </>
  );
}
