import { ArrowLeft, CheckCircle2, Clock, MapPin, NotebookPen, UploadCloud } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { errorMessage } from "../api/client";
import { Course, listCourses } from "../api/courses";
import { DAYS, LectureSlot, ReflectionResult, addReflection, getSlot, hhmm } from "../api/schedule";
import { runMyJobs } from "../api/jobs";
import { Alert, NewBadges, Spinner } from "../components/ui";

const PROMPTS = [
  "What was the main idea of today's lecture?",
  "Which new terms came up, and what do they mean?",
  "What is still unclear, and what will you ask about next time?",
];

/** Where the after-lecture reminder lands: capture what was learnt while it is fresh. */
export default function Reflect() {
  const { slotId } = useParams<{ slotId: string }>();
  const [slot, setSlot] = useState<LectureSlot | null>(null);
  const [courses, setCourses] = useState<Course[]>([]);
  const [courseId, setCourseId] = useState<string>("");
  const [content, setContent] = useState("");
  const [result, setResult] = useState<ReflectionResult | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!slotId) return;
    getSlot(slotId)
      .then((found) => {
        setSlot(found);
        setCourseId(found.course_id ?? "");
      })
      .catch(() => setError("Could not find that lecture. It may have been removed from your timetable."));
    listCourses().then(setCourses).catch(() => undefined);
  }, [slotId]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!slotId) return;
    setIsSaving(true);
    setError(null);
    try {
      setResult(await addReflection(slotId, content.trim(), courseId || null));
      runMyJobs();
    } catch (err) {
      setError(errorMessage(err, "Could not save your notes. Please try again."));
    } finally {
      setIsSaving(false);
    }
  }

  if (error && !slot) return <Alert>{error}</Alert>;
  if (!slot) return <Spinner />;

  if (result) {
    return (
      <div className="mx-auto max-w-xl animate-fade-in">
        <div className="card flex flex-col items-center p-6 text-center">
          <span className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-green-100 text-green-700">
            <CheckCircle2 className="h-6 w-6" aria-hidden />
          </span>
          <p className="font-semibold text-ink">Saved to your course notes</p>
          <p className="mt-1 text-sm text-ink/60">
            StudyMate is reading it now, so its ideas join your knowledge base, quizzes and games.
          </p>
          <div className="mt-4 w-full">
            <NewBadges badges={result.new_badges} />
          </div>
          <div className="mt-5 flex flex-wrap justify-center gap-2">
            <Link to={`/courses/${result.course_id}`} className="btn-secondary">
              <UploadCloud className="h-4 w-4" aria-hidden /> Upload the slides too
            </Link>
            <Link to="/schedule" className="btn-primary">
              Back to timetable
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl">
      <Link to="/schedule" className="btn-ghost -ml-2 mb-2">
        <ArrowLeft className="h-4 w-4" aria-hidden /> Timetable
      </Link>

      <div className="card overflow-hidden">
        <div className="bg-navy p-4 text-white">
          <p className="text-xs font-semibold uppercase tracking-wide text-gold">After the lecture</p>
          <h1 className="mt-1 text-xl font-bold">
            {slot.course_code && <span className="mr-2 text-gold">{slot.course_code}</span>}
            {slot.title}
          </h1>
          <p className="mt-1 flex flex-wrap gap-x-3 text-xs text-white/60">
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" aria-hidden />
              {DAYS[slot.day_of_week]} {hhmm(slot.start_time)}–{hhmm(slot.end_time)}
            </span>
            {slot.venue && (
              <span className="flex items-center gap-1">
                <MapPin className="h-3 w-3" aria-hidden />
                {slot.venue}
              </span>
            )}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 p-4">
          <div>
            <p className="flex items-center gap-1.5 text-sm font-semibold text-ink">
              <NotebookPen className="h-4 w-4 text-gold-dark" aria-hidden /> What did you learn?
            </p>
            <ul className="mt-1 list-disc space-y-0.5 pl-5 text-xs text-ink/55">
              {PROMPTS.map((prompt) => (
                <li key={prompt}>{prompt}</li>
              ))}
            </ul>
          </div>

          <textarea
            required
            rows={8}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="A few lines is plenty. Write it in your own words."
            className="input"
          />

          {!slot.course_id && (
            <label className="block">
              <span className="label">Which course is this for?</span>
              <select required value={courseId} onChange={(e) => setCourseId(e.target.value)} className="input mt-1">
                <option value="">Choose a course</option>
                {courses.map((course) => (
                  <option key={course.id} value={course.id}>
                    {course.code} - {course.name}
                  </option>
                ))}
              </select>
              <span className="mt-1 block text-xs text-ink/50">Remembered for next week&apos;s lecture.</span>
            </label>
          )}

          {error && <Alert>{error}</Alert>}

          <div className="flex flex-wrap items-center gap-2">
            <button type="submit" disabled={isSaving || !content.trim()} className="btn-primary">
              {isSaving ? "Saving..." : "Save to my notes"}
            </button>
            {slot.course_id && (
              <Link to={`/courses/${slot.course_id}`} className="btn-secondary">
                <UploadCloud className="h-4 w-4" aria-hidden /> Upload slides instead
              </Link>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
