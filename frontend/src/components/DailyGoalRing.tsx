import { Target } from "lucide-react";
import { Link } from "react-router-dom";

/** Today's study sessions against the daily goal, as a ring that fills up. */
export default function DailyGoalRing({ done, goal }: { done: number; goal: number }) {
  const fraction = Math.min(1, goal > 0 ? done / goal : 0);
  const reached = done >= goal;
  const radius = 26;
  const circumference = 2 * Math.PI * radius;

  return (
    <section className={`card mb-4 flex items-center gap-4 p-4 ${reached ? "border-green-300" : ""}`}>
      <div className="relative h-16 w-16 shrink-0">
        <svg viewBox="0 0 64 64" className="h-16 w-16 -rotate-90" aria-hidden>
          <circle cx="32" cy="32" r={radius} fill="none" strokeWidth="7" className="stroke-ink/10" />
          <circle
            cx="32"
            cy="32"
            r={radius}
            fill="none"
            strokeWidth="7"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={circumference * (1 - fraction)}
            className={`transition-[stroke-dashoffset] duration-700 ${reached ? "stroke-green-500" : "stroke-gold"}`}
          />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center text-sm font-bold tabular-nums text-ink">
          {Math.min(done, 99)}/{goal}
        </span>
      </div>
      <div className="min-w-0 flex-1">
        <p className="flex items-center gap-1.5 font-semibold text-ink">
          <Target className="h-4 w-4 text-gold-dark" aria-hidden /> Today's goal
        </p>
        <p className="text-sm text-ink/60" role="status">
          {reached
            ? "Goal reached. Nice work, see you tomorrow."
            : `${goal - done} more study session${goal - done === 1 ? "" : "s"} to go: a quiz, an Arcade round, or ten flashcards.`}
        </p>
      </div>
      <Link to="/settings" className="btn-ghost shrink-0 text-xs">
        Change
      </Link>
    </section>
  );
}
