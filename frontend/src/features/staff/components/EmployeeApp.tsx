import { NavLink, Navigate, Route, Routes } from "react-router-dom";

import { ThemeToggle } from "../../../shared/components/ThemeToggle";
import { useCurrentUser, useLogout } from "../../auth/hooks";
import { StaffLibrary } from "./StaffLibrary";

function EmployeeHome() {
  const { data: user } = useCurrentUser();

  return (
    <section>
      <div className="page-header">
        <div>
          <h1>Welcome{user ? `, ${user.name}` : ""}</h1>
          <p>The AI policies and information your organization has shared with you.</p>
        </div>
      </div>
      <h2>Policies and information</h2>
      <StaffLibrary />
    </section>
  );
}

/** What an employee login sees instead of the platform: a home page and
 * nothing else. Every other address comes back here -- the server refuses an
 * employee everything outside /staff anyway, so this is only so they don't
 * land on a page that can't load. */
export function EmployeeApp() {
  const { data: user } = useCurrentUser();
  const logout = useLogout();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="sidebar-brand-mark">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2l8 4v6c0 5-3.5 9-8 10-4.5-1-8-5-8-10V6l8-4z" />
            </svg>
          </div>
          <div>
            <div className="sidebar-brand-name">Governance</div>
            <div className="sidebar-brand-sub">Staff home</div>
          </div>
        </div>
        <nav aria-label="Sections">
          <div className="sidebar-group">
            <NavLink
              to="/"
              end
              className={({ isActive }) => `sidebar-link${isActive ? " active" : ""}`}
            >
              Home
            </NavLink>
          </div>
        </nav>
        <div className="sidebar-footer">
          <ThemeToggle />
          {user && (
            <div className="sidebar-account">
              <div className="sidebar-account-name">{user.name}</div>
              <button onClick={() => logout.mutate()} disabled={logout.isPending}>
                {logout.isPending ? "Signing out..." : "Sign out"}
              </button>
            </div>
          )}
        </div>
      </aside>
      <main className="main-content">
        <Routes>
          <Route path="/" element={<EmployeeHome />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
