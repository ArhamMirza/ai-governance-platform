import { useState } from "react";
import { Link, NavLink, Navigate, Route, Routes } from "react-router-dom";

import { ThemeToggle } from "../../../shared/components/ThemeToggle";
import { useCurrentUser, useLogout } from "../../auth/hooks";
import { ConcernSubmittedNotice } from "../../concerns/components/ConcernSubmittedNotice";
import { MyConcerns } from "../../concerns/components/MyConcerns";
import { ReportConcernForm } from "../../concerns/components/ReportConcernForm";
import type { ConcernSubmitted } from "../../concerns/types";
import { StaffLibrary } from "./StaffLibrary";

function EmployeeHome() {
  const { data: user } = useCurrentUser();

  return (
    <section>
      <div className="page-header">
        <div>
          <h1>Welcome{user ? `, ${user.name}` : ""}</h1>
          <p>
            If something about an AI system worries you, tell us. You can read the AI policies and
            information your organization has shared with you below.
          </p>
        </div>
      </div>
      <p>
        <Link to="/report" className="button-link">
          Report a concern
        </Link>{" "}
        <Link to="/concerns">My concerns</Link>
      </p>
      <h2>Policies and information</h2>
      <StaffLibrary />
    </section>
  );
}

function ReportConcernPage() {
  const [submitted, setSubmitted] = useState<ConcernSubmitted | null>(null);

  return (
    <section>
      <div className="page-header">
        <div>
          <h1>Report a concern</h1>
          <p>Something about an AI system that worries you -- you can stay anonymous.</p>
        </div>
      </div>
      {submitted ? (
        <ConcernSubmittedNotice result={submitted} />
      ) : (
        <ReportConcernForm onSubmitted={setSubmitted} />
      )}
    </section>
  );
}

function MyConcernsPage() {
  return (
    <section>
      <div className="page-header">
        <div>
          <h1>My concerns</h1>
          <p>What happened to the concerns you've raised.</p>
        </div>
      </div>
      <MyConcerns />
    </section>
  );
}

/** What an employee login sees instead of the platform: a home page, a way to
 * report a concern, and the concerns they've raised. Every other address comes
 * back here -- the server refuses an employee everything outside /staff
 * anyway, so this is only so they don't land on a page that can't load. */
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
            {(
              [
                ["/", "Home"],
                ["/report", "Report a concern"],
                ["/concerns", "My concerns"],
              ] as const
            ).map(([to, label]) => (
              <NavLink
                key={to}
                to={to}
                end
                className={({ isActive }) => `sidebar-link${isActive ? " active" : ""}`}
              >
                {label}
              </NavLink>
            ))}
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
          <Route path="/report" element={<ReportConcernPage />} />
          <Route path="/concerns" element={<MyConcernsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
