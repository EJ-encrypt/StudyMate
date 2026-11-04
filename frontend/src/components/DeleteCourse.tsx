import { Trash2 } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { errorMessage } from "../api/client";
import { Course, deleteCourse } from "../api/courses";
import { refreshCourses } from "../lib/courseLevels";
import { toast } from "../lib/toast";
import { Alert } from "./ui";

/** The bottom of a course page: delete it and everything made from it, after a second tap. */
export default function DeleteCourse({ course }: { course: Course }) {
  const navigate = useNavigate();
  const [isConfirming, setIsConfirming] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function remove() {
    setIsDeleting(true);
    setError(null);
    try {
      await deleteCourse(course.id);
      await refreshCourses().catch(() => undefined);
      toast(`${course.code} deleted.`);
      navigate(`/courses?level=${course.level}`, { replace: true });
    } catch (err) {
      setError(errorMessage(err, "Could not delete this course."));
      setIsDeleting(false);
    }
  }

  return (
    <section className="mt-10 border-t border-ink/10 pt-6">
      {!isConfirming ? (
        <button type="button" onClick={() => setIsConfirming(true)} className="btn-ghost text-red-600 hover:bg-red-50">
          <Trash2 className="h-4 w-4" aria-hidden /> Delete this course
        </button>
      ) : (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4">
          <p className="font-semibold text-red-700">
            Delete {course.code} and everything in it?
          </p>
          <p className="mt-1 text-sm text-red-700">
            Its uploaded files, question sets and answers, flashcard schedule, Coach progress and Arcade scores are
            deleted for good. Lectures on your timetable stay, and so do the XP and badges you have earned.
          </p>
          {error && (
            <div className="mt-3">
              <Alert>{error}</Alert>
            </div>
          )}
          <div className="mt-3 flex flex-wrap gap-2">
            <button type="button" onClick={() => void remove()} disabled={isDeleting} className="btn-danger">
              <Trash2 className="h-4 w-4" aria-hidden /> {isDeleting ? "Deleting..." : `Delete ${course.code}`}
            </button>
            <button type="button" onClick={() => setIsConfirming(false)} disabled={isDeleting} className="btn-ghost">
              Cancel
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
