import { CheckSquare, FileUp, Loader2, Square, X } from "lucide-react";
import { ChangeEvent, useState } from "react";

import { errorMessage } from "../api/client";
import { addCourses, CourseProposal, readCourseList } from "../api/courses";
import { useAuth } from "../context/AuthContext";
import { Alert } from "./ui";

const LEVELS = [100, 200, 300, 400, 500, 600];

/**
 * Which rows start ticked. A handbook page lists a whole programme; only
 * courses the document places in the chosen level and semester (or does not
 * place at all) are likely to be this semester's.
 */
function defaultTicks(proposals: CourseProposal[], level: number, semester: number): Set<number> {
  return new Set(
    proposals.flatMap((proposal, index) =>
      !proposal.already_added &&
      (proposal.level === null || proposal.level === level) &&
      (proposal.semester === null || proposal.semester === semester)
        ? [index]
        : [],
    ),
  );
}

/**
 * Upload a course list, registration slip or handbook page, then tick the
 * courses being taken this semester. Those are added under the level and
 * semester chosen here, which default to the student's current ones.
 */
export default function CourseImport({ onDone, onCancel }: { onDone: (added: number) => void; onCancel: () => void }) {
  const { user } = useAuth();
  const [proposals, setProposals] = useState<CourseProposal[] | null>(null);
  const [ticked, setTicked] = useState<Set<number>>(new Set());
  const [level, setLevel] = useState(user?.level ?? 100);
  const [semester, setSemester] = useState(user?.semester ?? 1);
  const [isReading, setIsReading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function choose(nextLevel: number, nextSemester: number) {
    setLevel(nextLevel);
    setSemester(nextSemester);
    if (proposals) setTicked(defaultTicks(proposals, nextLevel, nextSemester));
  }

  async function handleFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setIsReading(true);
    setError(null);
    try {
      const found = await readCourseList(file);
      setProposals(found);
      setTicked(defaultTicks(found, level, semester));
    } catch (err) {
      setError(errorMessage(err, "Could not read that file. Try a clearer photo or a PDF."));
    } finally {
      setIsReading(false);
    }
  }

  function toggle(index: number) {
    setTicked((previous) => {
      const next = new Set(previous);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }

  async function save() {
    if (!proposals) return;
    setIsSaving(true);
    setError(null);
    try {
      const chosen = [...ticked].sort((a, b) => a - b).map((index) => proposals[index]);
      const added = await addCourses(
        chosen.map((proposal) => ({
          code: proposal.code || proposal.name.slice(0, 50),
          name: proposal.name,
          level,
          semester,
        })),
      );
      onDone(added.length);
    } catch (err) {
      setError(errorMessage(err, "Could not add those courses."));
      setIsSaving(false);
    }
  }

  return (
    <section className="card mb-5 animate-fade-in p-4" aria-label="Import courses">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="font-semibold text-ink">Import courses from a file</h2>
          <p className="mt-0.5 text-sm text-ink/60">
            A photo or PDF of your registration slip, course list or programme handbook page.
          </p>
        </div>
        <button type="button" onClick={onCancel} aria-label="Close" className="btn-ghost -mr-2 -mt-1 p-1.5">
          <X className="h-4 w-4" aria-hidden />
        </button>
      </div>

      {!proposals && (
        <label
          className={[
            "mt-4 flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed px-4 py-8 text-center transition",
            isReading ? "border-gold bg-gold/5" : "border-ink/15 hover:border-gold hover:bg-gold/5",
          ].join(" ")}
        >
          {isReading ? (
            <>
              <Loader2 className="h-6 w-6 animate-spin text-gold-dark" aria-hidden />
              <span className="text-sm font-semibold text-ink">Reading your courses...</span>
              <span className="text-xs text-ink/55">Usually 10 to 30 seconds.</span>
            </>
          ) : (
            <>
              <FileUp className="h-6 w-6 text-gold-dark" aria-hidden />
              <span className="text-sm font-semibold text-ink">Choose a photo or PDF</span>
              <span className="text-xs text-ink/55">PNG, JPG, PDF or Word, up to 4MB</span>
            </>
          )}
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp,.pdf,.docx,.txt"
            onChange={handleFile}
            disabled={isReading}
            className="sr-only"
          />
        </label>
      )}

      {proposals && (
        <div className="mt-4">
          <p className="text-sm font-semibold text-ink">Which of these are you studying this semester?</p>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-ink/70">
            <span>Add them to</span>
            <select
              value={level}
              onChange={(e) => choose(Number(e.target.value), semester)}
              aria-label="Level"
              className="input w-auto py-1.5"
            >
              {LEVELS.map((value) => (
                <option key={value} value={value}>
                  Level {value}
                </option>
              ))}
            </select>
            <select
              value={semester}
              onChange={(e) => choose(level, Number(e.target.value))}
              aria-label="Semester"
              className="input w-auto py-1.5"
            >
              <option value={1}>Semester 1</option>
              <option value={2}>Semester 2</option>
            </select>
          </div>

          <ul className="mt-3 divide-y divide-ink/5 rounded-lg border border-ink/10">
            {proposals.map((proposal, index) => {
              const isTicked = ticked.has(index);
              return (
                <li key={`${proposal.code}-${index}`}>
                  <button
                    type="button"
                    role="checkbox"
                    aria-checked={proposal.already_added || isTicked}
                    disabled={proposal.already_added}
                    onClick={() => toggle(index)}
                    className="flex w-full items-center gap-3 px-3 py-2.5 text-left text-sm hover:bg-ink/5 disabled:cursor-default disabled:opacity-60 disabled:hover:bg-transparent"
                  >
                    {proposal.already_added || isTicked ? (
                      <CheckSquare className="h-5 w-5 shrink-0 text-gold-dark" aria-hidden />
                    ) : (
                      <Square className="h-5 w-5 shrink-0 text-ink/35" aria-hidden />
                    )}
                    <span className="min-w-0 flex-1">
                      <span className="font-semibold text-ink">{proposal.code || "No code"}</span>
                      <span className="text-ink/70"> · {proposal.name}</span>
                      {(proposal.level || proposal.semester) && (
                        <span className="block text-xs text-ink/45">
                          {[proposal.level && `Level ${proposal.level}`, proposal.semester && `Semester ${proposal.semester}`]
                            .filter(Boolean)
                            .join(" · ")}
                        </span>
                      )}
                    </span>
                    {proposal.already_added && <span className="text-xs text-ink/50">Already added</span>}
                  </button>
                </li>
              );
            })}
          </ul>

          {error && (
            <div className="mt-3">
              <Alert>{error}</Alert>
            </div>
          )}

          <div className="mt-4 flex flex-wrap gap-2">
            <button type="button" onClick={() => void save()} disabled={ticked.size === 0 || isSaving} className="btn-primary">
              {isSaving ? "Adding..." : `Add ${ticked.size} course${ticked.size === 1 ? "" : "s"}`}
            </button>
            <button type="button" onClick={() => setProposals(null)} className="btn-ghost">
              Try another file
            </button>
          </div>
        </div>
      )}

      {!proposals && error && (
        <div className="mt-3">
          <Alert>{error}</Alert>
        </div>
      )}
    </section>
  );
}
