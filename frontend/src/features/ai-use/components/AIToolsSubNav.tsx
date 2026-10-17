import { NavLink } from "react-router-dom";

const LINKS = [
  ["/ai-tools", "Tools and requests"],
  ["/ai-tools/rules", "Data rules"],
  ["/ai-tools/usage", "Usage"],
  ["/ai-tools/settings", "Settings"],
] as const;

/** The parts of managing staff use of AI tools, so each page can be
 * reached from the others. */
export function AIToolsSubNav() {
  return (
    <nav className="sheet-views" aria-label="AI tools sections">
      {LINKS.map(([to, label]) => (
        <NavLink
          key={to}
          to={to}
          end
          className={({ isActive }) => (isActive ? "active" : undefined)}
        >
          {label}
        </NavLink>
      ))}
    </nav>
  );
}
