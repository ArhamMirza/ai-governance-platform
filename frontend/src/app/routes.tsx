import { NavLink, Route, Routes } from "react-router-dom";

import { AISystemInventoryPage } from "../pages/AISystemInventoryPage";
import { DashboardPage } from "../pages/DashboardPage";
import { PoliciesPage } from "../pages/PoliciesPage";
import { PolicyDetailPage } from "../pages/PolicyDetailPage";
import { ProcedureDetailPage } from "../pages/ProcedureDetailPage";
import { ProceduresPage } from "../pages/ProceduresPage";
import { RiskAssessmentDetailPage } from "../pages/RiskAssessmentDetailPage";
import { RiskAssessmentsPage } from "../pages/RiskAssessmentsPage";

const navItems = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/policies", label: "Policies" },
  { to: "/procedures", label: "Procedures" },
  { to: "/ai-systems", label: "AI System Inventory" },
  { to: "/risk-assessments", label: "Risk Assessments" },
];

export function AppRoutes() {
  return (
    <div>
      <nav>
        <ul>
          {navItems.map((item) => (
            <li key={item.to}>
              <NavLink to={item.to} end={item.end}>
                {item.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <main>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/policies" element={<PoliciesPage />} />
          <Route path="/policies/:policyId" element={<PolicyDetailPage />} />
          <Route path="/procedures" element={<ProceduresPage />} />
          <Route path="/procedures/:procedureId" element={<ProcedureDetailPage />} />
          <Route path="/ai-systems" element={<AISystemInventoryPage />} />
          <Route path="/risk-assessments" element={<RiskAssessmentsPage />} />
          <Route
            path="/risk-assessments/:riskAssessmentId"
            element={<RiskAssessmentDetailPage />}
          />
        </Routes>
      </main>
    </div>
  );
}
