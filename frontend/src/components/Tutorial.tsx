import {
  ArrowLeft,
  ArrowRight,
  Brain,
  CalendarClock,
  Check,
  Gamepad2,
  GraduationCap,
  Library,
  LucideIcon,
  Settings,
  Trophy,
  UploadCloud,
  X,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";

import { updatePreferences } from "../api/auth";
import { useAuth } from "../context/AuthContext";
import { CoachIcon } from "../lib/icons";

interface Step {
  icon: LucideIcon;
  title: string;
  body: string;
  tip?: string;
}

/** In the same order as the tabs (Nav.tsx), which the test checks. */
export const STEPS: Step[] = [
  {
    icon: GraduationCap,
    title: "Welcome to StudyMate",
    body: "StudyMate turns your own lecture slides, PDFs and notes into revision: flashcards, quizzes, games and reminders. Here is how it works, in eight quick steps.",
  },
  {
    icon: Library,
    title: "1. Add your courses",
    body: "Start in My Courses. Add each course you are taking this semester, or import them all at once from a photo or PDF of your course list or registration slip.",
  },
  {
    icon: UploadCloud,
    title: "2. Add your material",
    body: "Open a course and upload its slides, PDFs or Word documents, type notes, or photograph the pages of notes you wrote in a book. StudyMate reads them, handwriting included, and pulls out the key concepts, usually within a minute or two.",
    tip: "Maths, statistics and economics files are read with their equations intact.",
  },
  {
    icon: Brain,
    title: "3. Revise in the Study Engine",
    body: "Pick a course in the Study Engine and generate flashcards, multiple choice, fill in the blank, short answers or a full exam paper, from one lecture or the whole course.",
    tip: "After turning a flashcard over, tap Still learning or Got it. Cards you know come back days later; the rest come back tomorrow.",
  },
  {
    icon: CoachIcon,
    title: "4. Follow your Coach",
    body: "The Coach tracks how well you know every concept from the questions you answer, picks up to five topics to revise next, and tells you when flashcards are due again.",
  },
  {
    icon: Gamepad2,
    title: "5. Play in the Arcade",
    body: "Five games built from your own material, from Beat the Clock to Three Strikes. Each round earns XP, and from the results screen you can challenge a friend to beat your score.",
  },
  {
    icon: Trophy,
    title: "6. Climb the Leaderboard",
    body: "On the Leaderboard, add friends by their username, compare XP this week or of all time, and play the challenges friends send you. You can also join the board for everyone on your programme.",
    tip: "On a phone, Leaderboard and Settings are the icons at the top right. Use the ... beside anyone to report or block them.",
  },
  {
    icon: CalendarClock,
    title: "7. Add your timetable",
    body: "In Timetable, enter your lectures or upload a photo of your timetable. StudyMate reminds you an hour before each lecture and when it starts, then asks what you learnt so it becomes notes.",
    tip: "On an iPhone, first add StudyMate to your Home Screen (Share, then Add to Home Screen): iPhones only send reminders to apps added that way.",
  },
  {
    icon: Settings,
    title: "8. Track your progress",
    body: "Profile shows your XP, day streak, badges and today's goal. In Settings you can set that daily goal, switch between light and dark mode, choose how reminders reach you, set a username, and change your password.",
    tip: "You can replay this tutorial from Settings at any time.",
  },
];

/**
 * First-run walkthrough, shown over the home page once onboarding is done.
 * Finishing or skipping both mark it seen on the account.
 */
export default function Tutorial() {
  const { user, refresh } = useAuth();
  const location = useLocation();
  const [step, setStep] = useState(0);
  const [isClosing, setIsClosing] = useState(false);
  const dialog = useRef<HTMLDivElement>(null);

  const open = !!user && !!user.school && !user.tutorial_seen && location.pathname === "/courses" && !isClosing;

  useEffect(() => {
    if (open) {
      setStep(0);
      dialog.current?.focus();
    }
  }, [open]);

  async function close() {
    setIsClosing(true);
    try {
      await updatePreferences({ tutorial_seen: true });
      await refresh();
    } catch {
      // Shown again next time, which is better than not closing at all.
    } finally {
      setIsClosing(false);
    }
  }

  useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") void close();
      if (event.key === "ArrowRight") setStep((value) => Math.min(value + 1, STEPS.length - 1));
      if (event.key === "ArrowLeft") setStep((value) => Math.max(value - 1, 0));
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  if (!open) return null;

  const current = STEPS[step];
  const Icon = current.icon;
  const isLast = step === STEPS.length - 1;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-navy-dark/60 p-3 backdrop-blur-sm sm:items-center">
      <div
        ref={dialog}
        role="dialog"
        aria-modal="true"
        aria-labelledby="tutorial-title"
        tabIndex={-1}
        className="card w-full max-w-md animate-pop overflow-hidden focus:outline-none"
      >
        <div className="relative bg-gradient-to-br from-navy to-navy-light px-6 pb-6 pt-7 text-white">
          <button
            type="button"
            onClick={() => void close()}
            aria-label="Skip the tutorial"
            className="absolute right-3 top-3 rounded-lg p-1.5 text-white/60 hover:bg-white/10 hover:text-white"
          >
            <X className="h-5 w-5" aria-hidden />
          </button>
          <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gold/20 text-gold">
            <Icon className="h-7 w-7" aria-hidden />
          </span>
          <h2 id="tutorial-title" className="mt-4 text-xl font-bold">
            {current.title}
          </h2>
        </div>
        <div className="p-6">
          <p className="text-sm leading-relaxed text-ink/80">{current.body}</p>
          {current.tip && (
            <p className="mt-3 rounded-lg border border-gold/40 bg-gold/10 px-3 py-2 text-xs text-ink/75">{current.tip}</p>
          )}

          <div className="mt-6 flex items-center justify-center gap-1.5" aria-label={`Step ${step + 1} of ${STEPS.length}`}>
            {STEPS.map((_, index) => (
              <button
                key={index}
                type="button"
                onClick={() => setStep(index)}
                aria-label={`Go to step ${index + 1}`}
                className={[
                  "h-2 rounded-full transition-all",
                  index === step ? "w-6 bg-gold" : "w-2 bg-ink/20 hover:bg-ink/35",
                ].join(" ")}
              />
            ))}
          </div>

          <div className="mt-6 flex items-center justify-between gap-2">
            {step === 0 ? (
              <button type="button" onClick={() => void close()} className="btn-ghost">
                Skip
              </button>
            ) : (
              <button type="button" onClick={() => setStep(step - 1)} className="btn-ghost">
                <ArrowLeft className="h-4 w-4" aria-hidden /> Back
              </button>
            )}
            {isLast ? (
              <button type="button" onClick={() => void close()} className="btn-primary">
                <Check className="h-4 w-4" aria-hidden /> Get started
              </button>
            ) : (
              <button type="button" onClick={() => setStep(step + 1)} className="btn-primary">
                {step === 0 ? "Show me" : "Next"} <ArrowRight className="h-4 w-4" aria-hidden />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
