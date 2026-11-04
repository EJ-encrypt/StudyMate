import { Plus, Save, Trash2, X } from "lucide-react";
import { FormEvent, useState } from "react";

import { addCourses } from "../api/courses";
import { errorMessage } from "../api/client";
import { Alert } from "./ui";

const LEVELS = [100, 200, 300, 400, 500, 600];

interface Row {
  key: number;
  code: string;
  name: string;
}

let nextKey = 1;
const blankRow = (): Row => ({ key: nextKey++, code: "", name: "" });

/**
 * Choose a level and semester, then type in as many of its courses as you
 * like and save them together.
 */
export default function AddCoursesForm({
  level: startLevel,
  semester: startSemester,
  fixed = false,
  onClose,
  onAdded,
}: {
  level: number;
  semester: number;
  /** Opened from a semester's own Add button: the courses go there, so there is nothing to choose. */
  fixed?: boolean;
  onClose: () => void;
  /** Called with how many were added, and how many were already in the list. */
  onAdded: (added: number, skipped: number, level: number) => void;
}) {
  const [level, setLevel] = useState(startLevel);
  const [semester, setSemester] = useState(startSemester);
  const [rows, setRows] = useState<Row[]>(() => [blankRow(), blankRow()]);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const filled = rows.filter((row) => row.code.trim() && row.name.trim());
  const halfFilled = rows.some((row) => !!row.code.trim() !== !!row.name.trim());

  function update(key: number, field: "code" | "name", value: string) {
    setRows((current) => current.map((row) => (row.key === key ? { ...row, [field]: value } : row)));
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (halfFilled) {
      setError("Each course needs both a code and a name. Clear a row to leave it out.");
      return;
    }
    if (filled.length === 0) return;
    setIsSaving(true);
    try {
      const added = await addCourses(
        filled.map((row) => ({ code: row.code.trim(), name: row.name.trim(), level, semester })),
      );
      onAdded(added.length, filled.length - added.length, level);
    } catch (err) {
      setError(errorMessage(err, "Could not add those courses."));
      setIsSaving(false);
    }
  }

  return (
    <form onSubmit={save} className="card mb-5 animate-fade-in p-4" data-tour="courses-add-form">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-semibold text-ink">
          {fixed ? `Add Level ${level}, Semester ${semester} courses` : "Add courses"}
        </h2>
        <button type="button" onClick={onClose} className="btn-ghost p-1.5" aria-label="Close">
          <X className="h-4 w-4" aria-hidden />
        </button>
      </div>

      {!fixed && (
        <div className="mb-4 grid grid-cols-2 gap-3 sm:w-80">
          <label>
            <span className="label">Level</span>
            <select value={level} onChange={(e) => setLevel(Number(e.target.value))} className="input mt-1">
              {LEVELS.map((value) => (
                <option key={value} value={value}>
                  Level {value}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="label">Semester</span>
            <select value={semester} onChange={(e) => setSemester(Number(e.target.value))} className="input mt-1">
              <option value={1}>Semester 1</option>
              <option value={2}>Semester 2</option>
            </select>
          </label>
        </div>
      )}

      <ul className="space-y-2">
        {rows.map((row, index) => (
          <li key={row.key} className="grid grid-cols-[6.5rem_1fr_auto] items-center gap-2 sm:grid-cols-[9rem_1fr_auto]">
            <input
              value={row.code}
              onChange={(e) => update(row.key, "code", e.target.value)}
              placeholder="Code"
              aria-label={`Course ${index + 1} code`}
              className="input"
            />
            <input
              value={row.name}
              onChange={(e) => update(row.key, "name", e.target.value)}
              placeholder="Course name"
              aria-label={`Course ${index + 1} name`}
              className="input"
            />
            <button
              type="button"
              onClick={() => setRows((current) => (current.length > 1 ? current.filter((r) => r.key !== row.key) : [blankRow()]))}
              aria-label={`Remove course ${index + 1}`}
              className="btn-ghost p-2 text-ink/40"
            >
              <Trash2 className="h-4 w-4" aria-hidden />
            </button>
          </li>
        ))}
      </ul>

      <button type="button" onClick={() => setRows((current) => [...current, blankRow()])} className="btn-ghost mt-2 text-gold-dark">
        <Plus className="h-4 w-4" aria-hidden /> Another course
      </button>

      {error && (
        <div className="mt-3">
          <Alert>{error}</Alert>
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button type="submit" disabled={isSaving || filled.length === 0} className="btn-primary">
          <Save className="h-4 w-4" aria-hidden />
          {isSaving
            ? "Saving..."
            : `Save ${filled.length || ""} course${filled.length === 1 ? "" : "s"}`.replace("  ", " ")}
        </button>
        {!fixed && (
          <span className="text-xs text-ink/50">
            Level {level}, Semester {semester}
          </span>
        )}
      </div>
    </form>
  );
}
