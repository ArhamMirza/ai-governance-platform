import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { AuditLogViewer } from "../../audit-log/components/AuditLogViewer";
import { useRiskCriteria } from "../../risk-criteria/hooks";
import { DataGrid } from "../../sheets/components/DataGrid";
import type { SheetRow } from "../../sheets/types";
import { useUserDirectory } from "../../users/hooks";
import { makeRiskAssessmentSheetAdapter } from "../api";
import { riskAssessmentSheetKey, useAISystemInventoryRows, useRiskAssessment } from "../hooks";
import { isRiskItemOverdue } from "../riskMonitoring";
import { RiskAssessmentHeader } from "./RiskAssessmentHeader";
import { RiskItemPanel } from "./RiskItemPanel";
import { RiskMatrix } from "./RiskMatrix";

const COMPUTED_COLUMNS = ["inherent_risk_score", "residual_risk_score"];

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

  if (isLoading) return <p>Loading risk assessment...</p>;
  if (isError || !riskAssessment) return <p>Failed to load risk assessment.</p>;

  const aiSystemRow = inventory?.rows.find((row) => row.id === riskAssessment.ai_system_row_id);
  const aiSystemName =
    aiSystemRow && typeof aiSystemRow.data.name === "string" && aiSystemRow.data.name
      ? aiSystemRow.data.name
      : `AI System #${riskAssessment.ai_system_row_id}`;

  const ownerOptions = (directory ?? []).map((user) => ({
    value: String(user.id),
    label: user.name,
  }));

  return (
    <article>
      <h2>Risk Assessment</h2>
      <RiskAssessmentHeader riskAssessment={riskAssessment} aiSystemName={aiSystemName} />

      <h3>Risk Items</h3>
      <DataGrid
        queryKey={[...queryKey]}
        adapter={adapter}
        readOnlyColumnKeys={COMPUTED_COLUMNS}
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

      <h3>Audit Log</h3>
      <AuditLogViewer entityType="RiskAssessment" entityId={riskAssessmentId} />
    </article>
  );
}
