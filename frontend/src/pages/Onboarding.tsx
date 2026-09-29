import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import { completeOnboarding } from "../api/auth";
import { useAuth } from "../context/AuthContext";

const LEVELS = [100, 200, 300, 400, 500, 600];

export default function Onboarding() {
  const { user, refresh } = useAuth();
  const navigate = useNavigate();
  const [school, setSchool] = useState("");
  const [programme, setProgramme] = useState("");
  const [level, setLevel] = useState(100);
  const [semester, setSemester] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setIsSaving(true);
    setError(null);
    try {
      await completeOnboarding({ school, programme, level, semester });
      await refresh();
      navigate("/courses");
    } catch {
      setError("Could not save your details. Please try again.");
    } finally {
      setIsSaving(false);
    }
  }

  const firstName = user?.full_name ? user.full_name.split(" ")[0] : "";

  return (
    <div className="mx-auto max-w-lg px-5 py-8">
      <h1 className="text-xl font-bold text-navy">
        Welcome{firstName ? `, ${firstName}` : ""}
      </h1>
      <p className="mt-1 text-sm text-navy/60">
        A few details, so your courses are filed under the right level and semester.
      </p>

      <form onSubmit={handleSubmit} className="mt-5 flex flex-col gap-3">
        <label className="text-sm font-semibold text-navy">
          School
          <input
            type="text"
            required
            value={school}
            onChange={(e) => setSchool(e.target.value)}
            placeholder="School of Physical and Mathematical Sciences"
            className="mt-1 w-full rounded border border-navy/20 px-3 py-1.5 text-sm font-normal"
          />
        </label>

        <label className="text-sm font-semibold text-navy">
          Programme of study
          <input
            type="text"
            required
            value={programme}
            onChange={(e) => setProgramme(e.target.value)}
            placeholder="BSc Information Technology"
            className="mt-1 w-full rounded border border-navy/20 px-3 py-1.5 text-sm font-normal"
          />
        </label>

        <div className="flex gap-3">
          <label className="flex-1 text-sm font-semibold text-navy">
            Level
            <select
              value={level}
              onChange={(e) => setLevel(Number(e.target.value))}
              className="mt-1 w-full rounded border border-navy/20 px-3 py-1.5 text-sm font-normal"
            >
              {LEVELS.map((value) => (
                <option key={value} value={value}>
                  Level {value}
                </option>
              ))}
            </select>
          </label>

          <label className="flex-1 text-sm font-semibold text-navy">
            Semester
            <select
              value={semester}
              onChange={(e) => setSemester(Number(e.target.value))}
              className="mt-1 w-full rounded border border-navy/20 px-3 py-1.5 text-sm font-normal"
            >
              <option value={1}>First semester</option>
              <option value={2}>Second semester</option>
            </select>
          </label>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={isSaving}
          className="w-fit rounded bg-navy px-4 py-1.5 text-sm font-semibold text-gold hover:bg-navy-light disabled:opacity-50"
        >
          {isSaving ? "Saving..." : "Continue"}
        </button>
      </form>
    </div>
  );
}
