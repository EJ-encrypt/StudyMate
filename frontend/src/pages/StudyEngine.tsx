import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Course, groupByLevelAndSemester, listCourses } from "../api/courses";
import PageHeader from "../components/PageHeader";

export default function StudyEngine() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listCourses()
      .then(setCourses)
      .catch(() => setError("Could not load your courses."));
  }, []);

  const groups = groupByLevelAndSemester(courses);
  const anyMaterial = courses.some((course) => course.document_count > 0);

  return (
    <>
      <PageHeader
        title="Study Engine"
        subtitle="Pick a course to generate revision material from what you have uploaded."
      />

      {error && <p className="mb-3 text-sm text-red-600">{error}</p>}

      {courses.length === 0 && (
        <p className="text-sm text-navy/60">
          No courses yet. Add one in{" "}
          <Link to="/courses" className="font-semibold text-gold-dark">
            My Courses
          </Link>
          .
        </p>
      )}

      {courses.length > 0 && !anyMaterial && (
        <p className="mb-4 rounded border border-gold/40 bg-gold/10 px-3 py-2 text-sm text-navy/75">
          None of your courses have material yet. Upload something from{" "}
          <Link to="/courses" className="font-semibold text-gold-dark">
            My Courses
          </Link>{" "}
          first.
        </p>
      )}

      {groups.map((group) => (
        <section key={group.key} className="mb-5">
          <h2 className="mb-2 text-xs font-bold uppercase tracking-wide text-navy/50">
            {group.label}
          </h2>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {group.courses.map((course) => {
              const ready = course.document_count > 0;
              const card = (
                <>
                  <p className="text-sm font-bold text-navy">{course.code}</p>
                  <p className="text-sm text-navy/75">{course.name}</p>
                  <p className="mt-1 text-xs text-navy/50">
                    {ready
                      ? `${course.document_count} file${course.document_count === 1 ? "" : "s"}`
                      : "No material yet"}
                  </p>
                </>
              );

              return ready ? (
                <Link
                  key={course.id}
                  to={`/study/${course.id}`}
                  className="rounded border border-navy/15 bg-white p-3 hover:border-gold hover:shadow-sm"
                >
                  {card}
                </Link>
              ) : (
                <div
                  key={course.id}
                  className="rounded border border-navy/10 bg-white p-3 opacity-60"
                >
                  {card}
                </div>
              );
            })}
          </div>
        </section>
      ))}
    </>
  );
}
