import { Route, Routes } from "react-router-dom";

import { AISystemInventoryPage } from "../pages/AISystemInventoryPage";
import { DashboardPage } from "../pages/DashboardPage";
import { FrameworksPage } from "../pages/FrameworksPage";
import { PoliciesPage } from "../pages/PoliciesPage";
import { PolicyDetailPage } from "../pages/PolicyDetailPage";
import { ProcedureDetailPage } from "../pages/ProcedureDetailPage";
import { ProceduresPage } from "../pages/ProceduresPage";
import { RiskAssessmentDetailPage } from "../pages/RiskAssessmentDetailPage";
import { RiskAssessmentsPage } from "../pages/RiskAssessmentsPage";
import { UsersPage } from "../pages/UsersPage";
import { Layout } from "./Layout";

export function AppRoutes() {
  return (
    <Layout>
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
        <Route path="/frameworks" element={<FrameworksPage />} />
        <Route path="/users" element={<UsersPage />} />
      </Routes>
    </Layout>
  );
}
