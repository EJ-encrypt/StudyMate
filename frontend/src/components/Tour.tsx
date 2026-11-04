import { ArrowLeft, ArrowRight, Check, X } from "lucide-react";
import { CSSProperties, useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { updatePreferences } from "../api/auth";
import { useAuth } from "../context/AuthContext";
import { startTour, stopTour, useTourActive } from "../lib/tour";

export interface TourStep {
  /** The page the step is on. */
  path: string;
  /** data-tour of the part to spotlight; the first one visible is used. None: a card in the middle. */
  target?: string;
  title: string;
  body: string;
}

/** A walk through every section, in the order of the tabs (the test checks). */
export const TOUR_STEPS: TourStep[] = [
  {
    path: "/courses",
    title: "Welcome to StudyMate",
    body: "StudyMate turns your own slides, PDFs and notes into flashcards, quizzes, games and reminders. This tour shows you where everything is and what to do there. It takes about a minute.",
  },
  {
    path: "/courses",
    target: "nav-courses",
    title: "My Courses",
    body: "Your courses, one level at a time, Semester 1 then Semester 2. When you move up a level, earlier levels and everything in them stay here. On a computer, open the arrow beside My Courses to switch level; on a phone, use the level chips at the top.",
  },
  {
    path: "/courses",
    target: "courses-add",
    title: "Add your courses",
    body: "Tap Add courses, choose the level and semester, and type in as many courses as you like before saving. Or use Import from file to read them from a photo or PDF of your registration slip.",
  },
  {
    path: "/courses",
    target: "courses-semester",
    title: "Add your material",
    body: "Open a course to give StudyMate something to work with: upload slides, PDFs or Word files, type notes, or photograph the pages of your notebook. It reads them, handwriting included, in a minute or two. You can delete a course at the bottom of its page.",
  },
  {
    path: "/study",
    target: "nav-study",
    title: "Study Engine",
    body: "Pick a course and generate flashcards, multiple choice, fill in the blank, short answers or a full exam paper, from one lecture or the whole course. After turning a flashcard over, tap Still learning or Got it, and it comes back when it is due.",
  },
  {
    path: "/study",
    target: "term-picker",
    title: "Revise any level",
    body: "Choose the level, then the semester, before the course. Moved on to Level 200? Switch back here to quiz yourself on Level 100. The Coach and the Arcade have the same choice.",
  },
  {
    path: "/coach",
    target: "nav-coach",
    title: "Coach",
    body: "The Coach tracks how well you know every concept from your answers and picks up to five topics to revise next. Tap a topic to see its concepts, where each is explained in your material, and how they fit together. It also tells you when flashcards are due.",
  },
  {
    path: "/play",
    target: "nav-arcade",
    title: "Arcade",
    body: "Five games built from your own material, from Beat the Clock to Three Strikes. Each round earns XP. From the results screen you can challenge a friend to beat your score on the same round.",
  },
  {
    path: "/friends",
    target: "nav-leaderboard",
    title: "Leaderboard",
    body: "Your XP is shown right here. Open it to add friends by username, compare XP this week or of all time, play the challenges friends send you, and join the board for everyone on your programme. Use the ... beside anyone to report or block them.",
  },
  {
    path: "/schedule",
    target: "nav-timetable",
    title: "Timetable",
    body: "Add your lectures, or upload a photo of your timetable. StudyMate reminds you an hour before each lecture and when it starts, then asks what you learnt so it becomes notes. Tap the pencil on a lecture to change its time, or the bin to remove it.",
  },
  {
    path: "/settings",
    target: "nav-settings",
    title: "Settings",
    body: "Your progress and badges, daily goal, profile and level, password, privacy, reminders, permissions and dark mode. On an iPhone, add StudyMate to your Home Screen (Share, then Add to Home Screen) so reminders can reach you.",
  },
  {
    path: "/settings",
    target: "settings-tour",
    title: "You're all set",
    body: "Start by adding this semester's courses and uploading a lecture. You can take this tour again any time from here.",
  },
];

const PAD = 6;
const GAP = 12;
const CARD_WIDTH = 340;

function findTarget(name: string): HTMLElement | null {
  const all = document.querySelectorAll<HTMLElement>(`[data-tour="${name}"]`);
  for (const element of all) {
    const rect = element.getBoundingClientRect();
    if (rect.width > 0 && rect.height > 0) return element;
  }
  return null;
}

/** Where the card goes: beside a sidebar item, else above or below the spotlight. */
function cardPlacement(rect: DOMRect | null, cardHeight: number): CSSProperties {
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const width = Math.min(CARD_WIDTH, vw - 32);
  if (!rect) return { width, left: (vw - width) / 2, top: Math.max(16, (vh - cardHeight) / 2) };
  if (vw >= 768 && rect.right < 280) {
    return { width, left: rect.right + GAP + PAD, top: Math.min(Math.max(16, rect.top - 24), vh - cardHeight - 16) };
  }
  const left = Math.min(Math.max(16, rect.left + rect.width / 2 - width / 2), vw - width - 16);
  const below = rect.bottom + PAD + GAP;
  if (below + cardHeight <= vh - 8) return { width, left, top: below };
  return { width, left, top: Math.max(16, rect.top - PAD - GAP - cardHeight) };
}

/**
 * The guided tour: goes to each section, dims the page around the part to
 * use, and says what to do there. Starts by itself once for a new student.
 */
export default function Tour() {
  const { user, refresh } = useAuth();
  const active = useTourActive();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [index, setIndex] = useState(0);
  const [rect, setRect] = useState<DOMRect | null>(null);
  const [cardHeight, setCardHeight] = useState(220);
  const card = useRef<HTMLDivElement>(null);
  const autoStarted = useRef(false);

  // A new student sees it once, after onboarding.
  useEffect(() => {
    if (user?.school && !user.tutorial_seen && !autoStarted.current) {
      autoStarted.current = true;
      startTour();
    }
  }, [user]);

  useEffect(() => {
    if (active) setIndex(0);
  }, [active]);

  const step = TOUR_STEPS[index];

  // Go to the step's page, then find its target once the page has drawn it.
  useEffect(() => {
    if (!active) return;
    if (pathname !== step.path) {
      navigate(step.path);
      return;
    }
    setRect(null);
    if (!step.target) return;
    let tries = 0;
    let element: HTMLElement | null = null;
    const timer = window.setInterval(() => {
      element = findTarget(step.target!);
      tries += 1;
      if (element || tries > 20) {
        window.clearInterval(timer);
        if (element) {
          const r = element.getBoundingClientRect();
          if (r.top < 0 || r.bottom > window.innerHeight) element.scrollIntoView({ block: "center" });
          setRect(element.getBoundingClientRect());
        }
      }
    }, 75);
    const follow = () => element && setRect(element.getBoundingClientRect());
    window.addEventListener("resize", follow);
    window.addEventListener("scroll", follow, true);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("resize", follow);
      window.removeEventListener("scroll", follow, true);
    };
  }, [active, step, pathname, navigate]);

  useLayoutEffect(() => {
    if (card.current) setCardHeight(card.current.offsetHeight);
  }, [index, active, rect]);

  const finish = useCallback(async () => {
    stopTour();
    if (user && !user.tutorial_seen) {
      try {
        await updatePreferences({ tutorial_seen: true });
        await refresh();
      } catch {
        // Shown again next time, which is better than not closing.
      }
    }
  }, [user, refresh]);

  useEffect(() => {
    if (!active) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") void finish();
      if (event.key === "ArrowRight") setIndex((i) => Math.min(i + 1, TOUR_STEPS.length - 1));
      if (event.key === "ArrowLeft") setIndex((i) => Math.max(i - 1, 0));
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [active, finish]);

  if (!active || !user) return null;

  const isLast = index === TOUR_STEPS.length - 1;
  const spotlight = rect && {
    top: rect.top - PAD,
    left: rect.left - PAD,
    width: rect.width + PAD * 2,
    height: rect.height + PAD * 2,
  };

  return (
    <div className="fixed inset-0 z-[60]" role="presentation">
      {/* Blocks taps on the page while the tour runs; the dimming is the spotlight's shadow. */}
      <div className={`absolute inset-0 ${spotlight ? "" : "bg-navy-dark/65"}`} />
      {spotlight && (
        <div
          className="pointer-events-none absolute rounded-xl ring-2 ring-gold transition-all duration-300"
          style={{ ...spotlight, boxShadow: "0 0 0 9999px rgb(6 21 48 / 0.65)" }}
          aria-hidden
        />
      )}
      <div
        ref={card}
        role="dialog"
        aria-modal="true"
        aria-labelledby="tour-title"
        className="card absolute animate-fade-in p-5 shadow-lift"
        style={cardPlacement(rect, cardHeight)}
      >
        <button
          type="button"
          onClick={() => void finish()}
          aria-label="End the tour"
          className="absolute right-2 top-2 rounded-lg p-1.5 text-ink/50 hover:bg-ink/5 hover:text-ink"
        >
          <X className="h-4 w-4" aria-hidden />
        </button>
        <p className="text-xs font-semibold uppercase tracking-wide text-gold-dark">
          {index + 1} of {TOUR_STEPS.length}
        </p>
        <h2 id="tour-title" className="mt-1 pr-6 text-lg font-bold text-ink">
          {step.title}
        </h2>
        <p className="mt-1.5 text-sm leading-relaxed text-ink/75">{step.body}</p>
        <div className="mt-4 flex items-center justify-between gap-2">
          {index === 0 ? (
            <button type="button" onClick={() => void finish()} className="btn-ghost">
              Skip
            </button>
          ) : (
            <button type="button" onClick={() => setIndex(index - 1)} className="btn-ghost">
              <ArrowLeft className="h-4 w-4" aria-hidden /> Back
            </button>
          )}
          {isLast ? (
            <button type="button" onClick={() => void finish()} className="btn-primary">
              <Check className="h-4 w-4" aria-hidden /> Done
            </button>
          ) : (
            <button type="button" onClick={() => setIndex(index + 1)} className="btn-primary">
              {index === 0 ? "Show me" : "Next"} <ArrowRight className="h-4 w-4" aria-hidden />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
