import { ArrowRight, GraduationCap } from "lucide-react";
import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import { browserTimezone, completeOnboarding } from "../api/auth";
import { Alert } from "../components/ui";
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
      // The browser's zone, so lecture reminders fire at local times.
      await completeOnboarding({ school, programme, level, semester, timezone: browserTimezone() });
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
    <div className="mx-auto max-w-lg animate-fade-in">
      <span className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-navy text-gold shadow-sm">
        <GraduationCap className="h-6 w-6" aria-hidden />
      </span>
      <h1 className="text-2xl font-bold tracking-tight text-ink">
        Welcome{firstName ? `, ${firstName}` : ""}
      </h1>
      <p className="mt-1 text-sm text-ink/60">
        A few details, so your courses are filed under the right level and semester.
      </p>

      <form onSubmit={handleSubmit} className="card mt-6 flex flex-col gap-4 p-5">
        <label>
          <span className="label">School</span>
          <input
            type="text"
            required
            value={school}
            onChange={(e) => setSchool(e.target.value)}
            placeholder="School of Physical and Mathematical Sciences"
            className="input mt-1"
          />
        </label>

        <label>
          <span className="label">Programme of study</span>
          <input
            type="text"
            required
            value={programme}
            onChange={(e) => setProgramme(e.target.value)}
            placeholder="BSc Information Technology"
            className="input mt-1"
          />
        </label>

        <div className="grid grid-cols-2 gap-3">
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
              <option value={1}>First semester</option>
              <option value={2}>Second semester</option>
            </select>
          </label>
        </div>

        {error && <Alert>{error}</Alert>}

        <button type="submit" disabled={isSaving} className="btn-primary w-fit">
          {isSaving ? "Saving..." : "Continue"}
          <ArrowRight className="h-4 w-4" aria-hidden />
        </button>
      </form>
    </div>
  );
}
