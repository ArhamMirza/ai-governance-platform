import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { ApiError } from "../../../shared/api/httpClient";
import { ConfirmDialog } from "../../../shared/components/ConfirmDialog";
import { ApprovalWithdrawalNotice } from "../../audit-log/ApprovalWithdrawalNotice";
import { AuditLogViewer } from "../../audit-log/components/AuditLogViewer";
import { ImpactAssessmentList } from "../../impact-assessments/components/ImpactAssessmentList";
import { useRiskCriteria } from "../../risk-criteria/hooks";
import { DataGrid } from "../../sheets/components/DataGrid";
import type { SheetRow } from "../../sheets/types";
import { formatUserOption } from "../../users/formatUserOption";
import { useUserDirectory } from "../../users/hooks";
import { makeRiskAssessmentSheetAdapter } from "../api";
import {
  riskAssessmentKey,
  riskAssessmentSheetKey,
  useAISystemInventoryRows,
  useDeleteRiskAssessment,
  useRiskAssessment,
} from "../hooks";
import { isRiskItemOverdue } from "../riskMonitoring";
import { RiskAssessmentHeader } from "./RiskAssessmentHeader";
import { RiskItemPanel } from "./RiskItemPanel";
import { RiskMatrix } from "./RiskMatrix";
import { RiskSuggestionPanel } from "./RiskSuggestionPanel";

const COMPUTED_COLUMNS = ["inherent_risk_score", "residual_risk_score"];
const LONG_TEXT_COLUMNS = ["description", "mitigation"];

interface RiskAssessmentDetailProps {
  riskAssessmentId: number;
}

export function RiskAssessmentDetail({ riskAssessmentId }: RiskAssessmentDetailProps) {
  const { data: riskAssessment, isLoading, isError } = useRiskAssessment(riskAssessmentId);
  const { data: inventory } = useAISystemInventoryRows();
  const { data: criteria } = useRiskCriteria();
  const { data: directory } = useUserDirectory();
  const adapter = makeRiskAssessmentSheetAdapter(riskAssessmentId);
  const queryKey = riskAssessmentSheetKey(riskAssessmentId);
  const { data: sheet } = useQuery({ queryKey, queryFn: adapter.get });
  const [managingRow, setManagingRow] = useState<SheetRow | null>(null);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const deleteRiskAssessment = useDeleteRiskAssessment();
  const navigate = useNavigate();

  if (isLoading) return <p>Loading risk assessment...</p>;
  if (isError || !riskAssessment) return <p>Failed to load risk assessment.</p>;

  const aiSystemRow = inventory?.rows.find((row) => row.id === riskAssessment.ai_system_row_id);
  const aiSystemName =
    aiSystemRow && typeof aiSystemRow.data.name === "string" && aiSystemRow.data.name
      ? aiSystemRow.data.name
      : `AI System #${riskAssessment.ai_system_row_id}`;

  const ownerOptions = (directory ?? []).map((user) => ({
    value: String(user.id),
    label: formatUserOption(user),
  }));

  const handleDelete = async () => {
    setDeleteError(null);
    try {
      await deleteRiskAssessment.mutateAsync(riskAssessmentId);
      navigate("/risk-assessments");
    } catch (err) {
      setDeleteError(
        err instanceof ApiError ? err.message : "Failed to delete risk assessment",
      );
    }
  };

  return (
    <article>
      <div className="page-header">
        <h2>Risk Assessment</h2>
        <button onClick={() => setConfirmingDelete(true)}>Delete Risk Assessment</button>
      </div>
      <RiskAssessmentHeader riskAssessment={riskAssessment} aiSystemName={aiSystemName} />

      <h3>Risk Items</h3>
      <ApprovalWithdrawalNotice status={riskAssessment.status} />
      <RiskSuggestionPanel riskAssessmentId={riskAssessmentId} />
      <DataGrid
        queryKey={[...queryKey]}
        adapter={adapter}
        // Editing an item can withdraw the assessment's approval server-side,
        // so the header and the dashboard have to be refetched with the sheet.
        alsoInvalidate={[
          [...riskAssessmentKey(riskAssessmentId)],
          ["dashboard-summary"],
          ["risk-portfolio-summary"],
        ]}
        readOnlyColumnKeys={COMPUTED_COLUMNS}
        longTextColumnKeys={LONG_TEXT_COLUMNS}
        isRowFlagged={isRiskItemOverdue}
        flaggedLabel="Overdue"
        selectOptions={{ risk_owner: ownerOptions }}
        rowActions={(row) => (
          <button onClick={() => setManagingRow(row)}>
            {row.data.status === "closed" ? "View" : "Manage"}
          </button>
        )}
      />

      {managingRow && (
        <RiskItemPanel
          riskAssessmentId={riskAssessmentId}
          row={sheet?.rows.find((row) => row.id === managingRow.id) ?? managingRow}
          onClose={() => setManagingRow(null)}
        />
      )}

      <h3>Risk Matrix</h3>
      <RiskMatrix rows={sheet?.rows ?? []} bands={criteria} />

      <h3>Impact Assessments</h3>
      <ImpactAssessmentList riskAssessmentId={riskAssessmentId} />

      <AuditLogViewer entityType="RiskAssessment" entityId={riskAssessmentId} />

      {confirmingDelete && (
        <ConfirmDialog
          title="Delete this risk assessment?"
          message={`This deletes every risk item on ${aiSystemName}'s risk assessment and the evidence attached to them. The AI system and its impact assessment are kept. This cannot be undone.`}
          confirmLabel="Delete Risk Assessment"
          isPending={deleteRiskAssessment.isPending}
          error={deleteError}
          onCancel={() => {
            setConfirmingDelete(false);
            setDeleteError(null);
          }}
          onConfirm={handleDelete}
        />
      )}
    </article>
  );
}
