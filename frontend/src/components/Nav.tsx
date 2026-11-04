import {
  Brain,
  CalendarClock,
  ChevronDown,
  Gamepad2,
  GraduationCap,
  Library,
  LogOut,
  LucideIcon,
  Settings,
  Trophy,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link, NavLink, useLocation, useSearchParams } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { useCourseLevels } from "../lib/courseLevels";
import { CoachIcon } from "../lib/icons";
import { formatXp, useXp } from "../lib/useXp";

interface NavItem {
  to: string;
  label: string;
  /** Shorter label for the phone tab bar, where width is tight. */
  short: string;
  icon: LucideIcon;
  /** Where the guided tour points (data-tour). */
  tour: string;
}

const COURSES: NavItem = { to: "/courses", label: "My Courses", short: "Courses", icon: Library, tour: "nav-courses" };
const STUDY: NavItem = { to: "/study", label: "Study Engine", short: "Study", icon: Brain, tour: "nav-study" };
const COACH: NavItem = { to: "/coach", label: "Coach", short: "Coach", icon: CoachIcon, tour: "nav-coach" };
const ARCADE: NavItem = { to: "/play", label: "Arcade", short: "Arcade", icon: Gamepad2, tour: "nav-arcade" };
const LEADERBOARD: NavItem = { to: "/friends", label: "Leaderboard", short: "Leaderboard", icon: Trophy, tour: "nav-leaderboard" };
const TIMETABLE: NavItem = { to: "/schedule", label: "Timetable", short: "Timetable", icon: CalendarClock, tour: "nav-timetable" };
const SETTINGS: NavItem = { to: "/settings", label: "Settings", short: "Settings", icon: Settings, tour: "nav-settings" };

/** Every page, in order, for the sidebar. Profile now lives inside Settings. */
export const NAV_ITEMS: NavItem[] = [COURSES, STUDY, COACH, ARCADE, LEADERBOARD, TIMETABLE, SETTINGS];

/** The phone tab bar has room for six; the Leaderboard sits in the phone header, with the XP. */
export const TAB_ITEMS = NAV_ITEMS.filter((item) => item !== LEADERBOARD);

function Brand() {
  return (
    <span className="flex items-center gap-2 text-base font-extrabold tracking-tight text-gold">
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gold/15">
        <GraduationCap className="h-5 w-5" aria-hidden />
      </span>
      StudyMate
    </span>
  );
}

function sidebarLink(isActive: boolean) {
  return [
    "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition",
    isActive ? "bg-white/10 font-semibold text-gold" : "text-white/70 hover:bg-white/5 hover:text-white",
  ].join(" ");
}

/** My Courses, opening to the levels; each level shows its two semesters. */
function CoursesLink() {
  const { pathname } = useLocation();
  const [params] = useSearchParams();
  const { levels: withCourses, current } = useCourseLevels();
  const onCourses = pathname.startsWith("/courses");
  const [isOpen, setIsOpen] = useState(onCourses);
  const shownLevel = Number(params.get("level")) || current;
  // A level just started has no courses yet, but is listed while it is open.
  const levels =
    onCourses && !withCourses.includes(shownLevel) ? [...withCourses, shownLevel].sort((a, b) => a - b) : withCourses;

  useEffect(() => {
    if (onCourses) setIsOpen(true);
  }, [onCourses]);

  return (
    <div>
      <div className="flex items-center">
        <NavLink to="/courses" data-tour={COURSES.tour} className={({ isActive }) => `${sidebarLink(isActive)} flex-1`}>
          <Library className="h-[18px] w-[18px] shrink-0" aria-hidden />
          {COURSES.label}
        </NavLink>
        {levels.length > 0 && (
          <button
            type="button"
            onClick={() => setIsOpen((open) => !open)}
            aria-expanded={isOpen}
            aria-label={isOpen ? "Hide levels" : "Show levels"}
            className="rounded-lg p-2 text-white/60 hover:bg-white/5 hover:text-white"
          >
            <ChevronDown className={`h-4 w-4 transition-transform ${isOpen ? "rotate-180" : ""}`} aria-hidden />
          </button>
        )}
      </div>
      {isOpen && levels.length > 0 && (
        <ul className="mb-1 ml-6 mt-0.5 space-y-0.5 border-l border-white/10 pl-2" aria-label="Levels">
          {levels.map((level) => {
            const active = pathname === "/courses" && shownLevel === level;
            return (
              <li key={level}>
                <Link
                  to={`/courses?level=${level}`}
                  aria-current={active ? "page" : undefined}
                  className={[
                    "block rounded-md px-3 py-1.5 text-sm transition",
                    active ? "bg-white/10 font-semibold text-gold" : "text-white/60 hover:bg-white/5 hover:text-white",
                  ].join(" ")}
                >
                  Level {level}
                  {level === current && <span className="ml-1.5 text-xs font-normal text-white/40">now</span>}
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

/** Left sidebar on tablets and desktops. */
export function Sidebar() {
  const { user, logout } = useAuth();
  const xp = useXp(!!user);
  if (!user) return null;

  return (
    <aside className="hidden w-60 shrink-0 bg-navy text-white md:block">
      <div className="sticky top-0 flex h-screen flex-col">
        <div className="border-b border-white/10 px-4 pb-4 pt-5">
          <Brand />
          <p className="mt-3 truncate text-sm font-medium text-white/85">{user.full_name}</p>
          {user.programme && (
            <p className="truncate text-xs text-white/50">
              {user.programme}
              {user.level ? ` · L${user.level}` : ""}
            </p>
          )}
        </div>

        <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 py-3">
          {NAV_ITEMS.map(({ to, label, icon: Icon, tour }) =>
            to === COURSES.to ? (
              <CoursesLink key={to} />
            ) : (
              <NavLink key={to} to={to} data-tour={tour} className={({ isActive }) => sidebarLink(isActive)}>
                <Icon className="h-[18px] w-[18px] shrink-0" aria-hidden />
                <span className="flex-1">{label}</span>
                {to === LEADERBOARD.to && xp !== null && (
                  <span className="rounded-full bg-gold/15 px-2 py-0.5 text-xs font-bold tabular-nums text-gold">
                    {formatXp(xp)}
                  </span>
                )}
              </NavLink>
            ),
          )}
        </nav>

        <button
          onClick={() => void logout()}
          className="m-2 flex items-center gap-3 rounded-lg px-3 py-2 text-left text-sm text-white/60 hover:bg-white/5 hover:text-white"
        >
          <LogOut className="h-[18px] w-[18px]" aria-hidden />
          Log out
        </button>
      </div>
    </aside>
  );
}

/** Slim header on phones: the brand, and the Leaderboard with the student's XP. */
export function MobileHeader() {
  const { user } = useAuth();
  const xp = useXp(!!user);
  if (!user) return null;
  return (
    <header className="sticky top-0 z-20 flex items-center justify-between bg-navy px-4 py-2.5 md:hidden">
      <Brand />
      <NavLink
        to={LEADERBOARD.to}
        data-tour={LEADERBOARD.tour}
        aria-label={xp === null ? "Leaderboard" : `Leaderboard, ${formatXp(xp)}`}
        className={({ isActive }) =>
          [
            "flex h-9 items-center gap-1.5 rounded-full px-3 transition",
            isActive ? "bg-white/20 text-gold" : "bg-white/10 text-white hover:bg-white/15",
          ].join(" ")
        }
      >
        <Trophy className="h-4 w-4 text-gold" aria-hidden />
        {xp !== null && <span className="text-sm font-bold tabular-nums">{formatXp(xp, true)}</span>}
      </NavLink>
    </header>
  );
}

/** Bottom tab bar on phones. */
export function TabBar() {
  const { user } = useAuth();
  if (!user) return null;

  return (
    <nav
      aria-label="Main"
      className="pb-safe fixed inset-x-0 bottom-0 z-20 border-t border-ink/10 bg-surface/95 backdrop-blur md:hidden"
    >
      <div className="grid grid-cols-6">
        {TAB_ITEMS.map(({ to, short, icon: Icon, tour }) => (
          <NavLink
            key={to}
            to={to}
            data-tour={tour}
            className={({ isActive }) =>
              [
                "flex flex-col items-center gap-0.5 py-2 text-[10px] font-medium",
                isActive ? "text-ink" : "text-ink/45",
              ].join(" ")
            }
          >
            {({ isActive }) => (
              <>
                <span
                  className={[
                    "flex h-7 w-11 items-center justify-center rounded-full transition",
                    isActive ? "bg-gold/25" : "",
                  ].join(" ")}
                >
                  <Icon className="h-5 w-5" aria-hidden />
                </span>
                {short}
              </>
            )}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
