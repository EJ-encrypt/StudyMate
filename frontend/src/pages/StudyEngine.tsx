import { Brain, Library } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Course, groupByLevelAndSemester, listCourses } from "../api/courses";
import CourseCard from "../components/CourseCard";
import PageHeader from "../components/PageHeader";
import { Alert, EmptyState, ListSkeleton } from "../components/ui";

export default function StudyEngine() {
  const [courses, setCourses] = useState<Course[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listCourses()
      .then(setCourses)
      .catch(() => {
        setCourses([]);
        setError("Could not load your courses.");
      });
  }, []);

  const groups = groupByLevelAndSemester(courses ?? []);
  const anyMaterial = (courses ?? []).some((course) => course.document_count > 0);

  return (
    <>
      <PageHeader
        icon={Brain}
        title="Study Engine"
        subtitle="Pick a course to generate flashcards, quizzes and exam papers from your material."
      />

      {error && (
        <div className="mb-4">
          <Alert>{error}</Alert>
        </div>
      )}
      {courses === null && <ListSkeleton grid rows={3} />}

      {courses?.length === 0 && (
        <EmptyState
          icon={Library}
          title="No courses yet"
          action={
            <Link to="/courses" className="btn-primary">
              Go to My Courses
            </Link>
          }
        >
          Add a course and upload some material first.
        </EmptyState>
      )}

      {courses && courses.length > 0 && !anyMaterial && (
        <div className="mb-4">
          <Alert kind="info">
            None of your courses have material yet. Upload something from{" "}
            <Link to="/courses" className="font-semibold text-gold-dark underline">
              My Courses
            </Link>{" "}
            first.
          </Alert>
        </div>
      )}

      {groups.map((group) => (
        <section key={group.key} className="mb-6">
          <h2 className="section-title">{group.label}</h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {group.courses.map((course) => (
              <CourseCard
                key={course.id}
                course={course}
                to={`/study/${course.id}`}
                disabled={course.document_count === 0}
              />
            ))}
          </div>
        </section>
      ))}
    </>
  );
}
