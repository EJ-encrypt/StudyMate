import { Brain, Library } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Course, listCourses } from "../api/courses";
import CourseCard from "../components/CourseCard";
import PageHeader from "../components/PageHeader";
import TermPicker from "../components/TermPicker";
import { Alert, EmptyState, ListSkeleton } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { coursesIn, startingTerm, Term } from "../lib/term";

export default function StudyEngine() {
  const { user } = useAuth();
  const [courses, setCourses] = useState<Course[] | null>(null);
  const [term, setTerm] = useState<Term | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listCourses()
      .then((fetched) => {
        setCourses(fetched);
        setTerm(startingTerm(fetched, { level: user?.level ?? undefined, semester: user?.semester ?? undefined }));
      })
      .catch(() => {
        setCourses([]);
        setError("Could not load your courses.");
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const shown = coursesIn(courses ?? [], term);
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

      {courses && courses.length > 0 && (
        <>
          <div className="mb-4">
            <TermPicker courses={courses} term={term} onChange={setTerm} />
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {shown.map((course) => (
              <CourseCard
                key={course.id}
                course={course}
                to={`/study/${course.id}`}
                disabled={course.document_count === 0}
              />
            ))}
          </div>
        </>
      )}
    </>
  );
}
