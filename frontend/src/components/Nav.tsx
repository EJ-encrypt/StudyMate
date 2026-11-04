import {
  Brain,
  CalendarClock,
  Gamepad2,
  GraduationCap,
  Library,
  LogOut,
  LucideIcon,
  Settings,
  Target,
  UserCircle,
} from "lucide-react";
import { NavLink } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

interface NavItem {
  to: string;
  label: string;
  /** Shorter label for the phone tab bar, where width is tight. */
  short: string;
  icon: LucideIcon;
}

export const NAV_ITEMS: NavItem[] = [
  { to: "/courses", label: "My Courses", short: "Courses", icon: Library },
  { to: "/study", label: "Study Engine", short: "Study", icon: Brain },
  { to: "/play", label: "Arcade", short: "Arcade", icon: Gamepad2 },
  { to: "/schedule", label: "Timetable", short: "Timetable", icon: CalendarClock },
  { to: "/coach", label: "Coach", short: "Coach", icon: Target },
  { to: "/profile", label: "Profile", short: "Profile", icon: UserCircle },
];

/** In the sidebar and the phone header, not the tab bar, which has no room for a seventh tab. */
export const SETTINGS_ITEM: NavItem = { to: "/settings", label: "Settings", short: "Settings", icon: Settings };

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

/** Left sidebar on tablets and desktops. */
export function Sidebar() {
  const { user, logout } = useAuth();
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
          {[...NAV_ITEMS, SETTINGS_ITEM].map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                [
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition",
                  isActive
                    ? "bg-white/10 font-semibold text-gold"
                    : "text-white/70 hover:bg-white/5 hover:text-white",
                ].join(" ")
              }
            >
              <Icon className="h-[18px] w-[18px] shrink-0" aria-hidden />
              {label}
            </NavLink>
          ))}
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

/** Slim header on phones, where the sidebar is replaced by a tab bar. */
export function MobileHeader() {
  const { user } = useAuth();
  if (!user) return null;
  return (
    <header className="sticky top-0 z-20 flex items-center justify-between bg-navy px-4 py-2.5 md:hidden">
      <Brand />
      <div className="flex min-w-0 items-center gap-1">
        <span className="max-w-[40vw] truncate text-xs text-white/60">
          {user.username ? `@${user.username}` : user.full_name}
        </span>
        <NavLink
          to={SETTINGS_ITEM.to}
          aria-label="Settings"
          className={({ isActive }) =>
            [
              "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition",
              isActive ? "bg-white/10 text-gold" : "text-white/70 hover:bg-white/10 hover:text-white",
            ].join(" ")
          }
        >
          <Settings className="h-5 w-5" aria-hidden />
        </NavLink>
      </div>
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
        {NAV_ITEMS.map(({ to, short, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
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
