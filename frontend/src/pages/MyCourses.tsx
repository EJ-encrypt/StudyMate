import { FileUp, Library } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { updatePreferences } from "../api/auth";
import { errorMessage } from "../api/client";
import AddCoursesForm from "../components/AddCoursesForm";
import CourseCard from "../components/CourseCard";
import CourseImport from "../components/CourseImport";
import PageHeader from "../components/PageHeader";
import { Alert, EmptyState, ListSkeleton } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { refreshCourses, useCourseLevels } from "../lib/courseLevels";
import { toast } from "../lib/toast";

const HIGHEST_LEVEL = 900;

/**
 * Courses one level at a time, Semester 1 then Semester 2. Earlier levels
 * stay here when the student moves up: the sidebar (or, on a phone, the level
 * chips) switches between them.
 */
export default function MyCourses() {
  const { user, refresh } = useAuth();
  const { courses, levels, current } = useCourseLevels();
  const [params, setParams] = useSearchParams();
  const [adding, setAdding] = useState<{ semester: number; fixed: boolean } | null>(null);
  const [isImporting, setIsImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // File counts change as material is uploaded elsewhere, so re-read on arrival.
  useEffect(() => {
    refreshCourses().catch(() => setError("Could not load your courses."));
  }, []);

  const level = Number(params.get("level")) || current;
  const shownLevels = levels.includes(level) ? levels : [...levels, level].sort((a, b) => a - b);
  const inLevel = (courses ?? []).filter((course) => course.level === level);
  const nextLevel = Math.max(...shownLevels) + 100;

  function showLevel(value: number) {
    setParams({ level: String(value) });
    setAdding(null);
    setIsImporting(false);
  }

  async function makeCurrent() {
    try {
      await updatePreferences({ level, semester: 1 });
      await refresh();
      toast(`Level ${level} is now your current level.`);
    } catch (err) {
      setError(errorMessage(err, "Could not change your level."));
    }
  }

  const header = (
    <PageHeader
      icon={Library}
      title="My Courses"
      subtitle={user?.school ?? "Everything you are studying, by level and semester."}
      actions={
        <>
          <button
            type="button"
            onClick={() => {
              setIsImporting((open) => !open);
              setAdding(null);
            }}
            className="btn-secondary"
          >
            <FileUp className="h-4 w-4" aria-hidden /> Import from file
          </button>
          <button
            type="button"
            data-tour="courses-add"
            onClick={() => {
              setAdding((open) => (open ? null : { semester: user?.semester ?? 1, fixed: false }));
              setIsImporting(false);
            }}
            className="btn-primary"
          >
            Add courses
          </button>
        </>
      }
    />
  );

  return (
    <>
      {header}

      {/* Phones have no sidebar, so the levels are chips here. */}
      <div className="-mx-4 mb-4 flex gap-2 overflow-x-auto px-4 pb-1 md:hidden" data-tour="courses-levels">
        {shownLevels.map((value) => (
          <button
            key={value}
            type="button"
            onClick={() => showLevel(value)}
            aria-pressed={value === level}
            className={[
              "shrink-0 rounded-full px-3.5 py-1.5 text-sm font-semibold transition",
              value === level ? "bg-navy text-gold" : "bg-ink/5 text-ink/70",
            ].join(" ")}
          >
            Level {value}
          </button>
        ))}
        {nextLevel <= HIGHEST_LEVEL && (
          <button
            type="button"
            onClick={() => showLevel(nextLevel)}
            className="shrink-0 rounded-full border border-ink/15 bg-surface px-3.5 py-1.5 text-sm font-semibold text-ink shadow-sm"
          >
            Start Level {nextLevel}
          </button>
        )}
      </div>

      {adding && (
        <AddCoursesForm
          level={level}
          semester={adding.semester}
          fixed={adding.fixed}
          onClose={() => setAdding(null)}
          onAdded={async (added, skipped, addedTo) => {
            setAdding(null);
            await refreshCourses();
            toast(
              `Added ${added} course${added === 1 ? "" : "s"}${skipped ? `; ${skipped} ${skipped === 1 ? "was" : "were"} already in your list` : ""}.`,
            );
            if (addedTo !== level) showLevel(addedTo);
          }}
        />
      )}

      {isImporting && (
        <CourseImport
          defaultLevel={level}
          onCancel={() => setIsImporting(false)}
          onDone={async (added) => {
            setIsImporting(false);
            await refreshCourses();
            toast(added ? `Added ${added} course${added === 1 ? "" : "s"}.` : "Those courses were already in your list.");
          }}
        />
      )}

      {error && (
        <div className="mb-4">
          <Alert>{error}</Alert>
        </div>
      )}

      {courses === null && <ListSkeleton grid rows={3} />}

      {courses?.length === 0 && !adding && !isImporting && (
        <EmptyState
          icon={Library}
          title="No courses yet"
          action={
            <div className="flex flex-wrap justify-center gap-2">
              <button type="button" onClick={() => setAdding({ semester: user?.semester ?? 1, fixed: false })} className="btn-primary">
                Add your courses
              </button>
              <button type="button" onClick={() => setIsImporting(true)} className="btn-secondary">
                <FileUp className="h-4 w-4" aria-hidden /> Import from a photo or PDF
              </button>
            </div>
          }
        >
          Add this semester's courses by hand, several at once, or import them from your registration slip. Then
          upload slides, PDFs or notes to start revising.
        </EmptyState>
      )}

      {courses && courses.length > 0 && (
        <>
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-lg font-bold text-ink">
              Level {level}
              {level === user?.level && (
                <span className="ml-2 rounded-full bg-gold/20 px-2 py-0.5 align-middle text-xs font-semibold text-ink/70">
                  Current level
                </span>
              )}
            </h2>
            <div className="flex flex-wrap gap-2">
              {level !== user?.level && (
                <button
                  type="button"
                  onClick={() => void makeCurrent()}
                  className="rounded-full border border-ink/15 bg-surface px-3.5 py-1 text-sm font-semibold text-ink shadow-sm transition hover:border-gold hover:bg-gold/10"
                >
                  Make this my current level
                </button>
              )}
              {nextLevel <= HIGHEST_LEVEL && level === Math.max(...shownLevels) && (
                <button
                  type="button"
                  onClick={() => showLevel(nextLevel)}
                  className="hidden rounded-full border border-ink/15 bg-surface px-3.5 py-1 text-sm font-semibold text-ink shadow-sm transition hover:border-gold hover:bg-gold/10 md:inline-flex"
                >
                  Start Level {nextLevel}
                </button>
              )}
            </div>
          </div>

          {[1, 2].map((semester) => {
            const list = inLevel.filter((course) => course.semester === semester);
            return (
              <section key={semester} className="mb-6" data-tour={semester === 1 ? "courses-semester" : undefined}>
                <div className="mb-2 flex items-center justify-between">
                  <h3 className="section-title mb-0">Semester {semester}</h3>
                  {list.length > 0 && (
                    <button
                      type="button"
                      onClick={() => setAdding({ semester, fixed: true })}
                      className="rounded-full border border-ink/15 bg-surface px-3.5 py-1 text-xs font-semibold text-ink shadow-sm transition hover:border-gold hover:bg-gold/10"
                    >
                      Add
                    </button>
                  )}
                </div>
                {list.length === 0 ? (
                  <button
                    type="button"
                    onClick={() => setAdding({ semester, fixed: true })}
                    className="flex w-full items-center justify-center gap-2 rounded-xl border-2 border-dashed border-ink/15 px-4 py-6 text-sm font-semibold text-ink/55 transition hover:border-gold/60 hover:bg-gold/5"
                  >
                    Add Semester {semester} courses
                  </button>
                ) : (
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    {list.map((course) => (
                      <CourseCard key={course.id} course={course} to={`/courses/${course.id}`} />
                    ))}
                  </div>
                )}
              </section>
            );
          })}

          {inLevel.length === 0 && (
            <p className="text-sm text-ink/60">
              Starting Level {level}? Add its courses above. Your earlier levels stay in{" "}
              <Link to="/courses" className="font-semibold text-gold-dark">
                My Courses
              </Link>{" "}
              with everything you uploaded.
            </p>
          )}
        </>
      )}
    </>
  );
}
