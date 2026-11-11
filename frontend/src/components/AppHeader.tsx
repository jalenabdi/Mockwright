import { NavLink, useNavigate } from "react-router";

import { useAuth } from "../lib/auth";
import { Logo } from "./ui";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `text-[14px] transition-colors duration-150 ${isActive ? "font-semibold text-fg" : "text-muted hover:text-fg"}`;

export function AppHeader() {
  const { logout } = useAuth();
  const navigate = useNavigate();

  return (
    <header className="border-b border-line/70">
      <div className="mx-auto flex h-16 max-w-[1140px] items-center justify-between px-4 sm:px-6">
        <Logo to="/interviews/new" />
        <nav className="flex items-center gap-5 sm:gap-7" aria-label="Main">
          <NavLink to="/interviews/new" className={linkClass}>
            New Interview
          </NavLink>
          <NavLink to="/history" className={linkClass}>
            History
          </NavLink>
          <button
            type="button"
            onClick={() => {
              logout();
              navigate("/");
            }}
            className="text-[14px] text-muted transition-colors duration-150 hover:text-fg"
          >
            Log Out
          </button>
        </nav>
      </div>
    </header>
  );
}
