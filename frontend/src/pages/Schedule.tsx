import {
  BellRing,
  CalendarClock,
  CalendarPlus,
  Clock,
  FileImage,
  Loader2,
  MapPin,
  NotebookPen,
  Pencil,
  Trash2,
  Wand2,
  X,
} from "lucide-react";
import { FormEvent, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { errorMessage } from "../api/client";
import { Course, listCourses } from "../api/courses";
import {
  DAYS,
  LectureSlot,
  SHORT_DAYS,
  SlotInput,
  SlotProposal,
  createSlot,
  createSlots,
  deleteSlot,
  hhmm,
  listSlots,
  readTimetable,
  todayIndex,
  updateSlot,
} from "../api/schedule";
import NotificationSettings from "../components/NotificationSettings";
import PageHeader from "../components/PageHeader";
import { Alert, EmptyState, Spinner } from "../components/ui";

const BLANK: SlotInput = {
  title: "",
  course_id: null,
  day_of_week: todayIndex(),
  start_time: "08:30",
  end_time: "10:30",
  venue: "",
};

function SlotFields({
  value,
  courses,
  onChange,
  compact = false,
}: {
  value: SlotInput;
  courses: Course[];
  onChange: (next: SlotInput) => void;
  compact?: boolean;
}) {
  const set = (patch: Partial<SlotInput>) => onChange({ ...value, ...patch });
  return (
    <div className={compact ? "grid gap-2 sm:grid-cols-6" : "grid gap-3 sm:grid-cols-2"}>
      <label className={compact ? "sm:col-span-2" : "sm:col-span-2"}>
        {!compact && <span className="label">Lecture</span>}
        <input
          required
          value={value.title}
          onChange={(e) => set({ title: e.target.value })}
          placeholder="Database Systems"
          className="input mt-1"
          aria-label="Lecture"
        />
      </label>
      <label className={compact ? "sm:col-span-2" : ""}>
        {!compact && <span className="label">Course (for notes and reminders)</span>}
        <select
          value={value.course_id ?? ""}
          onChange={(e) => {
            const course = courses.find((c) => c.id === e.target.value);
            set({ course_id: course?.id ?? null, title: value.title || course?.name || "" });
          }}
          className="input mt-1"
          aria-label="Course"
        >
          <option value="">Not linked</option>
          {courses.map((course) => (
            <option key={course.id} value={course.id}>
              {course.code} - {course.name}
            </option>
          ))}
        </select>
      </label>
      <label className={compact ? "sm:col-span-2" : ""}>
        {!compact && <span className="label">Day</span>}
        <select
          value={value.day_of_week}
          onChange={(e) => set({ day_of_week: Number(e.target.value) })}
          className="input mt-1"
          aria-label="Day"
        >
          {DAYS.map((day, index) => (
            <option key={day} value={index}>
              {day}
            </option>
          ))}
        </select>
      </label>
      <div className={compact ? "grid grid-cols-2 gap-2 sm:col-span-2" : "grid grid-cols-2 gap-3"}>
        <label>
          {!compact && <span className="label">Starts</span>}
          <input
            type="time"
            required
            value={hhmm(value.start_time)}
            onChange={(e) => set({ start_time: e.target.value })}
            className="input mt-1"
            aria-label="Starts"
          />
        </label>
        <label>
          {!compact && <span className="label">Ends</span>}
          <input
            type="time"
            required
            value={hhmm(value.end_time)}
            onChange={(e) => set({ end_time: e.target.value })}
            className="input mt-1"
            aria-label="Ends"
          />
        </label>
      </div>
      <label className={compact ? "sm:col-span-2" : "sm:col-span-2"}>
        {!compact && <span className="label">Venue</span>}
        <input
          value={value.venue}
          onChange={(e) => set({ venue: e.target.value })}
          placeholder="JQB 19"
          className="input mt-1"
          aria-label="Venue"
        />
      </label>
    </div>
  );
}

type Editing = { id: string | null; value: SlotInput } | null;

export default function Schedule() {
  const [slots, setSlots] = useState<LectureSlot[] | null>(null);
  const [courses, setCourses] = useState<Course[]>([]);
  const [editing, setEditing] = useState<Editing>(null);
  const [proposals, setProposals] = useState<(SlotProposal & { keep: boolean })[] | null>(null);
  const [replaceExisting, setReplaceExisting] = useState(false);
  const [isReading, setIsReading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  async function refresh() {
    setSlots(await listSlots());
  }

  useEffect(() => {
    refresh().catch(() => {
      setSlots([]);
      setError("Could not load your timetable.");
    });
    listCourses().then(setCourses).catch(() => undefined);
  }, []);

  async function handleSave(event: FormEvent) {
    event.preventDefault();
    if (!editing) return;
    setIsSaving(true);
    setError(null);
    try {
      if (editing.id) await updateSlot(editing.id, editing.value);
      else await createSlot(editing.value);
      setEditing(null);
      await refresh();
    } catch (err) {
      setError(errorMessage(err, "Could not save that lecture. Check the end time is after the start."));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDelete(slot: LectureSlot) {
    if (!window.confirm(`Remove ${slot.title} on ${DAYS[slot.day_of_week]}?`)) return;
    await deleteSlot(slot.id);
    await refresh();
  }

  async function handleFile(file: File | undefined) {
    if (!file) return;
    setIsReading(true);
    setError(null);
    setNotice(null);
    setEditing(null);
    try {
      const found = await readTimetable(file);
      setProposals(found.map((p) => ({ ...p, keep: true })));
      setReplaceExisting((slots?.length ?? 0) > 0);
    } catch (err) {
      setError(errorMessage(err, "Could not read that timetable. Try a clearer photo, or add lectures by hand."));
    } finally {
      setIsReading(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  async function saveProposals() {
    if (!proposals) return;
    const chosen = proposals.filter((p) => p.keep);
    if (chosen.length === 0) return;
    setIsSaving(true);
    setError(null);
    try {
      await createSlots(
        chosen.map(({ title, course_id, day_of_week, start_time, end_time, venue }) => ({
          title,
          course_id,
          day_of_week,
          start_time: hhmm(start_time),
          end_time: hhmm(end_time),
          venue,
        })),
        replaceExisting,
      );
      setProposals(null);
      setNotice(`Saved ${chosen.length} lecture${chosen.length === 1 ? "" : "s"}. Reminders are on their way.`);
      await refresh();
    } catch (err) {
      setError(errorMessage(err, "Could not save those lectures. Check each one has a valid time."));
    } finally {
      setIsSaving(false);
    }
  }

  const today = todayIndex();
  // Start the week from today, so the next lectures are always at the top.
  const dayOrder = [...Array(7).keys()].map((offset) => (today + offset) % 7);
  const byDay = new Map<number, LectureSlot[]>();
  for (const slot of slots ?? []) {
    byDay.set(slot.day_of_week, [...(byDay.get(slot.day_of_week) ?? []), slot]);
  }

  return (
    <>
      <PageHeader
        icon={CalendarClock}
        title="Timetable"
        subtitle="Get reminded before each lecture, and prompted afterwards to capture what you learnt."
        actions={
          <>
            <button
              type="button"
              onClick={() => fileInput.current?.click()}
              disabled={isReading}
              className="btn-gold"
            >
              {isReading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Wand2 className="h-4 w-4" aria-hidden />}
              {isReading ? "Reading..." : "Upload timetable"}
            </button>
            <button type="button" onClick={() => setEditing({ id: null, value: BLANK })} className="btn-primary">
              <CalendarPlus className="h-4 w-4" aria-hidden /> Add lecture
            </button>
          </>
        }
      />
      <input
        ref={fileInput}
        type="file"
        accept="image/*,.pdf,.docx,.txt"
        className="sr-only"
        onChange={(e) => void handleFile(e.target.files?.[0])}
      />

      {error && (
        <div className="mb-4">
          <Alert>{error}</Alert>
        </div>
      )}
      {notice && (
        <div className="mb-4">
          <Alert kind="success">{notice}</Alert>
        </div>
      )}

      {isReading && (
        <div className="card mb-5 flex items-center gap-3 p-4 text-sm text-ink/70">
          <FileImage className="h-5 w-5 text-gold-dark" aria-hidden />
          Reading your timetable. This can take up to a minute.
        </div>
      )}

      {proposals && (
        <section className="card mb-6 animate-fade-in p-4">
          <div className="mb-3 flex items-start justify-between gap-3">
            <div>
              <h2 className="font-semibold text-ink">Check what was read</h2>
              <p className="text-sm text-ink/60">
                Fix anything that is wrong and untick anything that is not a lecture. Nothing is saved until you
                confirm.
              </p>
            </div>
            <button type="button" onClick={() => setProposals(null)} className="btn-ghost" aria-label="Discard">
              <X className="h-4 w-4" aria-hidden />
            </button>
          </div>
          <ul className="space-y-3">
            {proposals.map((proposal, index) => (
              <li
                key={index}
                className={`flex items-start gap-3 rounded-lg border p-3 ${proposal.keep ? "border-ink/10" : "border-dashed border-ink/10 opacity-50"}`}
              >
                <input
                  type="checkbox"
                  checked={proposal.keep}
                  onChange={(e) =>
                    setProposals((prev) => prev!.map((p, i) => (i === index ? { ...p, keep: e.target.checked } : p)))
                  }
                  className="mt-3 h-4 w-4 accent-ink"
                  aria-label="Keep this lecture"
                />
                <div className="flex-1">
                  <SlotFields
                    compact
                    courses={courses}
                    value={proposal}
                    onChange={(next) =>
                      setProposals((prev) => prev!.map((p, i) => (i === index ? { ...p, ...next } : p)))
                    }
                  />
                </div>
              </li>
            ))}
          </ul>
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            {(slots?.length ?? 0) > 0 ? (
              <label className="flex items-center gap-2 text-sm text-ink/70">
                <input
                  type="checkbox"
                  checked={replaceExisting}
                  onChange={(e) => setReplaceExisting(e.target.checked)}
                  className="h-4 w-4 accent-ink"
                />
                Replace my current timetable
              </label>
            ) : (
              <span />
            )}
            <button type="button" onClick={saveProposals} disabled={isSaving} className="btn-primary">
              Save {proposals.filter((p) => p.keep).length} lectures
            </button>
          </div>
        </section>
      )}

      {editing && (
        <form onSubmit={handleSave} className="card mb-6 animate-fade-in p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-semibold text-ink">{editing.id ? "Edit lecture" : "Add a lecture"}</h2>
            <button type="button" onClick={() => setEditing(null)} className="btn-ghost" aria-label="Close">
              <X className="h-4 w-4" aria-hidden />
            </button>
          </div>
          <SlotFields courses={courses} value={editing.value} onChange={(value) => setEditing({ ...editing, value })} />
          <button type="submit" disabled={isSaving} className="btn-primary mt-4">
            {isSaving ? "Saving..." : "Save lecture"}
          </button>
        </form>
      )}

      {slots === null && <Spinner />}

      {slots?.length === 0 && !proposals && !editing && (
        <EmptyState
          icon={CalendarClock}
          title="Your week is empty"
          action={
            <div className="flex flex-wrap justify-center gap-2">
              <button type="button" onClick={() => fileInput.current?.click()} className="btn-gold">
                <Wand2 className="h-4 w-4" aria-hidden /> Upload a timetable
              </button>
              <button type="button" onClick={() => setEditing({ id: null, value: BLANK })} className="btn-secondary">
                Add one by hand
              </button>
            </div>
          }
        >
          Upload a photo, screenshot or PDF of your timetable and StudyMate will read it, or add lectures one at a
          time.
        </EmptyState>
      )}

      {slots && slots.length > 0 && (
        <section className="space-y-4">
          {dayOrder
            .filter((day) => byDay.has(day))
            .map((day) => (
              <div key={day}>
                <h2 className="section-title">
                  {DAYS[day]}
                  {day === today && <span className="rounded-full bg-gold px-2 py-0.5 text-[10px] text-navy-dark">Today</span>}
                </h2>
                <ul className="space-y-2">
                  {byDay.get(day)!.map((slot) => (
                    <li key={slot.id} className="card flex items-center gap-3 p-3">
                      <div className="flex w-14 shrink-0 flex-col items-center rounded-lg bg-navy py-1.5 text-white">
                        <span className="text-[10px] font-semibold uppercase text-gold">{SHORT_DAYS[day]}</span>
                        <span className="text-sm font-bold">{hhmm(slot.start_time)}</span>
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="line-clamp-2 text-sm font-semibold text-ink">
                          {slot.course_code && <span className="mr-1.5 text-gold-dark">{slot.course_code}</span>}
                          {slot.title}
                        </p>
                        <p className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-ink/55">
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" aria-hidden />
                            {hhmm(slot.start_time)}–{hhmm(slot.end_time)}
                          </span>
                          {slot.venue && (
                            <span className="flex items-center gap-1">
                              <MapPin className="h-3 w-3" aria-hidden />
                              {slot.venue}
                            </span>
                          )}
                        </p>
                      </div>
                      <div className="flex shrink-0 items-center">
                        <Link to={`/lectures/${slot.id}/reflect`} className="btn-ghost" title="Write what you learnt">
                          <NotebookPen className="h-4 w-4" aria-hidden />
                          <span className="sr-only">Reflect</span>
                        </Link>
                        <button
                          type="button"
                          onClick={() =>
                            setEditing({
                              id: slot.id,
                              value: {
                                title: slot.title,
                                course_id: slot.course_id,
                                day_of_week: slot.day_of_week,
                                start_time: hhmm(slot.start_time),
                                end_time: hhmm(slot.end_time),
                                venue: slot.venue,
                              },
                            })
                          }
                          className="btn-ghost"
                          title="Edit"
                        >
                          <Pencil className="h-4 w-4" aria-hidden />
                          <span className="sr-only">Edit</span>
                        </button>
                        <button type="button" onClick={() => void handleDelete(slot)} className="btn-ghost hover:text-red-600" title="Remove">
                          <Trash2 className="h-4 w-4" aria-hidden />
                          <span className="sr-only">Remove</span>
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
        </section>
      )}

      <section className="mt-8">
        <h2 className="section-title">
          <BellRing className="h-3.5 w-3.5" aria-hidden /> Reminders
        </h2>
        <NotificationSettings />
      </section>
    </>
  );
}
