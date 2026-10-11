import { Route, Routes } from "react-router-dom";

import { AISystemDetailPage } from "../pages/AISystemDetailPage";
import { AISystemInventoryPage } from "../pages/AISystemInventoryPage";
import { ArchivePage } from "../pages/ArchivePage";
import { ChangeDetailPage } from "../pages/ChangeDetailPage";
import { ChangesPage } from "../pages/ChangesPage";
import { AuditDetailPage } from "../pages/AuditDetailPage";
import { AuditProgramDetailPage } from "../pages/AuditProgramDetailPage";
import { AuditProgramsPage } from "../pages/AuditProgramsPage";
import { CompetencePage } from "../pages/CompetencePage";
import { CompetenceRequirementDetailPage } from "../pages/CompetenceRequirementDetailPage";
import { CorrectiveActionDetailPage } from "../pages/CorrectiveActionDetailPage";
import { CorrectiveActionsPage } from "../pages/CorrectiveActionsPage";
import { DashboardPage } from "../pages/DashboardPage";
import { DataInventoryPage } from "../pages/DataInventoryPage";
import { FrameworksPage } from "../pages/FrameworksPage";
import { GovernanceRolesPage } from "../pages/GovernanceRolesPage";
import { HandbookPage } from "../pages/HandbookPage";
import { ImpactAssessmentDetailPage } from "../pages/ImpactAssessmentDetailPage";
import { IncidentDetailPage } from "../pages/IncidentDetailPage";
import { IncidentsPage } from "../pages/IncidentsPage";
import { ManagementReviewMeetingDetailPage } from "../pages/ManagementReviewMeetingDetailPage";
import { ManagementReviewPage } from "../pages/ManagementReviewPage";
import { ObjectiveDetailPage } from "../pages/ObjectiveDetailPage";
import { ObjectivesPage } from "../pages/ObjectivesPage";
import { OrganizationContextPage } from "../pages/OrganizationContextPage";
import { PoliciesPage } from "../pages/PoliciesPage";
import { PolicyDetailPage } from "../pages/PolicyDetailPage";
import { ProcedureDetailPage } from "../pages/ProcedureDetailPage";
import { ProceduresPage } from "../pages/ProceduresPage";
import { RiskAssessmentDetailPage } from "../pages/RiskAssessmentDetailPage";
import { RiskAssessmentsPage } from "../pages/RiskAssessmentsPage";
import { SettingsPage } from "../pages/SettingsPage";
import { SupplierDetailPage } from "../pages/SupplierDetailPage";
import { SuppliersPage } from "../pages/SuppliersPage";
import { UsersPage } from "../pages/UsersPage";
import { Layout } from "./Layout";

export function AppRoutes() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/organization-context" element={<OrganizationContextPage />} />
        <Route path="/policies" element={<PoliciesPage />} />
        <Route path="/policies/:policyId" element={<PolicyDetailPage />} />
        <Route path="/procedures" element={<ProceduresPage />} />
        <Route path="/procedures/:procedureId" element={<ProcedureDetailPage />} />
        <Route path="/ai-systems" element={<AISystemInventoryPage />} />
        <Route path="/ai-systems/:rowId" element={<AISystemDetailPage />} />
        <Route path="/data-inventory" element={<DataInventoryPage />} />
        <Route path="/changes" element={<ChangesPage />} />
        <Route path="/changes/:changeId" element={<ChangeDetailPage />} />
        <Route path="/objectives" element={<ObjectivesPage />} />
        <Route path="/objectives/:objectiveId" element={<ObjectiveDetailPage />} />
        <Route path="/suppliers" element={<SuppliersPage />} />
        <Route path="/suppliers/:supplierId" element={<SupplierDetailPage />} />
        <Route path="/archive" element={<ArchivePage />} />
        <Route path="/risk-assessments" element={<RiskAssessmentsPage />} />
        <Route
          path="/impact-assessments/:impactAssessmentId"
          element={<ImpactAssessmentDetailPage />}
        />
        <Route
          path="/risk-assessments/:riskAssessmentId"
          element={<RiskAssessmentDetailPage />}
        />
        <Route path="/competence" element={<CompetencePage />} />
        <Route
          path="/competence/:requirementId"
          element={<CompetenceRequirementDetailPage />}
        />
        <Route path="/incidents" element={<IncidentsPage />} />
        <Route path="/incidents/:incidentId" element={<IncidentDetailPage />} />
        <Route path="/corrective-actions" element={<CorrectiveActionsPage />} />
        <Route
          path="/corrective-actions/:correctiveActionId"
          element={<CorrectiveActionDetailPage />}
        />
        <Route path="/audit-programs" element={<AuditProgramsPage />} />
        <Route path="/audit-programs/:programId" element={<AuditProgramDetailPage />} />
        <Route
          path="/audit-programs/:programId/audits/:auditId"
          element={<AuditDetailPage />}
        />
        <Route path="/management-review" element={<ManagementReviewPage />} />
        <Route
          path="/management-review/:meetingId"
          element={<ManagementReviewMeetingDetailPage />}
        />
        <Route path="/frameworks" element={<FrameworksPage />} />
        <Route path="/governance" element={<GovernanceRolesPage />} />
        <Route path="/users" element={<UsersPage />} />
        <Route path="/handbook" element={<HandbookPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </Layout>
  );
}
