import { FileUp, Library, Plus, X } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { Course, createCourse, groupByLevelAndSemester, listCourses } from "../api/courses";
import CourseCard from "../components/CourseCard";
import CourseImport from "../components/CourseImport";
import PageHeader from "../components/PageHeader";
import { Alert, EmptyState, Spinner } from "../components/ui";
import { useAuth } from "../context/AuthContext";

const LEVELS = [100, 200, 300, 400, 500, 600];

export default function MyCourses() {
  const { user } = useAuth();
  const [courses, setCourses] = useState<Course[] | null>(null);
  const [isAdding, setIsAdding] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [level, setLevel] = useState(user?.level ?? 100);
  const [semester, setSemester] = useState(user?.semester ?? 1);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listCourses()
      .then(setCourses)
      .catch(() => {
        setCourses([]);
        setError("Could not load your courses.");
      });
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

  const groups = groupByLevelAndSemester(courses ?? []);

  return (
    <>
      <PageHeader
        icon={Library}
        title="My Courses"
        subtitle={user?.school ?? "Everything you are studying, by level and semester."}
        actions={
          <>
            <button
              type="button"
              onClick={() => {
                setIsImporting((prev) => !prev);
                setIsAdding(false);
              }}
              className="btn-secondary"
            >
              <FileUp className="h-4 w-4" aria-hidden /> Import from file
            </button>
            <button
              type="button"
              onClick={() => {
                setIsAdding((prev) => !prev);
                setIsImporting(false);
              }}
              className="btn-primary"
            >
              {isAdding ? <X className="h-4 w-4" aria-hidden /> : <Plus className="h-4 w-4" aria-hidden />}
              {isAdding ? "Cancel" : "Add course"}
            </button>
          </>
        }
      />

      {isAdding && (
        <form onSubmit={handleAdd} className="card mb-5 grid animate-fade-in gap-3 p-4 sm:grid-cols-[8rem_1fr_7rem_7rem_auto] sm:items-end">
          <label>
            <span className="label">Code</span>
            <input required value={code} onChange={(e) => setCode(e.target.value)} placeholder="CS302" className="input mt-1" />
          </label>
          <label>
            <span className="label">Course name</span>
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Database Systems"
              className="input mt-1"
            />
          </label>
          <label>
            <span className="label">Level</span>
            <select value={level} onChange={(e) => setLevel(Number(e.target.value))} className="input mt-1">
              {LEVELS.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="label">Semester</span>
            <select value={semester} onChange={(e) => setSemester(Number(e.target.value))} className="input mt-1">
              <option value={1}>1</option>
              <option value={2}>2</option>
            </select>
          </label>
          <button type="submit" className="btn-primary">
            Save
          </button>
        </form>
      )}

      {isImporting && (
        <CourseImport
          onCancel={() => setIsImporting(false)}
          onDone={async (added) => {
            setIsImporting(false);
            setNotice(added ? `Added ${added} course${added === 1 ? "" : "s"}.` : "Those courses were already in your list.");
            setCourses(await listCourses());
          }}
        />
      )}

      {notice && (
        <div className="mb-4">
          <Alert kind="success">{notice}</Alert>
        </div>
      )}

      {error && (
        <div className="mb-4">
          <Alert>{error}</Alert>
        </div>
      )}

      {courses === null && <Spinner />}

      {courses?.length === 0 && !isAdding && !isImporting && (
        <EmptyState
          icon={Library}
          title="No courses yet"
          action={
            <div className="flex flex-wrap justify-center gap-2">
              <button type="button" onClick={() => setIsAdding(true)} className="btn-primary">
                <Plus className="h-4 w-4" aria-hidden /> Add your first course
              </button>
              <button type="button" onClick={() => setIsImporting(true)} className="btn-secondary">
                <FileUp className="h-4 w-4" aria-hidden /> Import from a photo or PDF
              </button>
            </div>
          }
        >
          Add your courses by hand, or import them from your registration slip or course list. Then upload slides,
          PDFs or notes to start revising.
        </EmptyState>
      )}

      {groups.map((group) => (
        <section key={group.key} className="mb-6">
          <h2 className="section-title">{group.label}</h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {group.courses.map((course) => (
              <CourseCard key={course.id} course={course} to={`/courses/${course.id}`} />
            ))}
          </div>
        </section>
      ))}
    </>
  );
}
