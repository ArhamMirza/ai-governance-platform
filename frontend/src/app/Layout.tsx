import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";

import { useCurrentUser, useLogout } from "../features/auth/hooks";
import { hasPermission } from "../features/auth/permissions";

interface NavItem {
  to: string;
  label: string;
  end?: boolean;
  icon: ReactNode;
}

const usersNavItem: NavItem = {
  to: "/users",
  label: "Users",
  icon: (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  ),
};

const navItems: NavItem[] = [
  {
    to: "/",
    label: "Dashboard",
    end: true,
    icon: (
      <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="7" height="7" rx="1.5" />
        <rect x="14" y="3" width="7" height="7" rx="1.5" />
        <rect x="3" y="14" width="7" height="7" rx="1.5" />
        <rect x="14" y="14" width="7" height="7" rx="1.5" />
      </svg>
    ),
  },
  {
    to: "/policies",
    label: "Policies",
    icon: (
      <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <path d="M14 2v6h6" />
        <path d="M9 13h6M9 17h6" />
      </svg>
    ),
  },
  {
    to: "/procedures",
    label: "Procedures",
    icon: (
      <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="6" y="4" width="12" height="16" rx="2" />
        <path d="M9 4V3a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v1" />
        <path d="M9 12l2 2 4-4" />
      </svg>
    ),
  },
  {
    to: "/ai-systems",
    label: "AI System Inventory",
    icon: (
      <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="6" y="6" width="12" height="12" rx="2" />
        <rect x="10" y="10" width="4" height="4" />
        <path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3" />
      </svg>
    ),
  },
  {
    to: "/risk-assessments",
    label: "Risk Assessments",
    icon: (
      <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 2l8 3.5v6c0 5-3.4 8.7-8 10-4.6-1.3-8-5-8-10v-6z" />
        <path d="M12 8v5M12 16h.01" />
      </svg>
    ),
  },
  {
    to: "/frameworks",
    label: "Frameworks",
    icon: (
      <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
        <path d="M9 7h7M9 11h7" />
      </svg>
    ),
  },
];

export function Layout({ children }: { children: ReactNode }) {
  const { data: user } = useCurrentUser();
  const logout = useLogout();
  const items = hasPermission(user?.role, "manage_users")
    ? [...navItems, usersNavItem]
    : navItems;

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
            <div className="sidebar-brand-sub">AI Compliance Platform</div>
          </div>
        </div>
        <nav>
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => `sidebar-link${isActive ? " active" : ""}`}
            >
              {item.icon}
              {item.label}
            </NavLink>
          ))}
        </nav>
        {user && (
          <div className="sidebar-account">
            <div className="sidebar-account-name">{user.name}</div>
            <div className="sidebar-account-role">{user.role}</div>
            <button onClick={() => logout.mutate()} disabled={logout.isPending}>
              {logout.isPending ? "Signing out..." : "Sign out"}
            </button>
          </div>
        )}
      </aside>
      <main className="main-content">{children}</main>
    </div>
  );
}
