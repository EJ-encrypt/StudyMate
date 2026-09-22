import { NavLink } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

const NAV_LINKS = [
  { to: "/upload", label: "Upload" },
  { to: "/materials", label: "Materials" },
  { to: "/coach", label: "Coach" },
  { to: "/profile", label: "Profile" },
];

export default function Nav() {
  const { user, logout } = useAuth();

  return (
    <nav className="bg-navy text-white">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
        <span className="text-lg font-bold text-gold">StudyMate AI</span>
        {user && (
          <div className="flex items-center gap-6">
            {NAV_LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                className={({ isActive }) =>
                  isActive ? "text-gold font-semibold" : "text-white/80 hover:text-gold"
                }
              >
                {link.label}
              </NavLink>
            ))}
            <button onClick={logout} className="text-white/80 hover:text-gold">
              Log out
            </button>
          </div>
        )}
      </div>
    </nav>
  );
}
