import { NavLink } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

const LINKS = [
  { to: "/courses", label: "My Courses" },
  { to: "/study", label: "Study Engine" },
  { to: "/coach", label: "Coach" },
  { to: "/profile", label: "Profile" },
];

/** Left sidebar, after the Sakai portal's site/tool list. */
export default function Nav() {
  const { user, logout } = useAuth();
  if (!user) return null;

  return (
    <aside className="w-56 shrink-0 border-r border-navy/15 bg-navy text-white">
      <div className="sticky top-0 flex h-screen flex-col">
        <div className="border-b border-white/10 px-4 py-3">
          <span className="text-base font-bold text-gold">StudyMate</span>
          <p className="mt-0.5 truncate text-xs text-white/60">{user.full_name}</p>
          {user.programme && (
            <p className="truncate text-xs text-white/45">
              {user.programme}
              {user.level ? ` · L${user.level}` : ""}
            </p>
          )}
        </div>

        <nav className="flex-1 overflow-y-auto py-1">
          {LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                [
                  "block border-l-[3px] px-4 py-2 text-sm",
                  isActive
                    ? "border-gold bg-white/10 font-semibold text-gold"
                    : "border-transparent text-white/75 hover:bg-white/5 hover:text-white",
                ].join(" ")
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>

        <button
          onClick={logout}
          className="border-t border-white/10 px-4 py-2.5 text-left text-sm text-white/70 hover:bg-white/5 hover:text-white"
        >
          Log out
        </button>
      </div>
    </aside>
  );
}
