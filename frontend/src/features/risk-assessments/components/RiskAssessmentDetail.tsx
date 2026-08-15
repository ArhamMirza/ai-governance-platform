import { useQuery } from "@tanstack/react-query";

import { DataGrid } from "../../sheets/components/DataGrid";
import { makeRiskAssessmentSheetAdapter } from "../api";
import { riskAssessmentSheetKey, useAISystemInventoryRows, useRiskAssessment } from "../hooks";
import { isRiskItemOverdue } from "../riskMonitoring";
import { RiskAssessmentHeader } from "./RiskAssessmentHeader";
import { RiskMatrix } from "./RiskMatrix";

const COMPUTED_COLUMNS = ["inherent_risk_score", "residual_risk_score"];

interface RiskAssessmentDetailProps {
  riskAssessmentId: number;
}

export function RiskAssessmentDetail({ riskAssessmentId }: RiskAssessmentDetailProps) {
  const { data: riskAssessment, isLoading, isError } = useRiskAssessment(riskAssessmentId);
  const { data: inventory } = useAISystemInventoryRows();
  const adapter = makeRiskAssessmentSheetAdapter(riskAssessmentId);
  const queryKey = riskAssessmentSheetKey(riskAssessmentId);
  const { data: sheet } = useQuery({ queryKey, queryFn: adapter.get });

  if (isLoading) return <p>Loading risk assessment...</p>;
  if (isError || !riskAssessment) return <p>Failed to load risk assessment.</p>;

  const aiSystemRow = inventory?.rows.find((row) => row.id === riskAssessment.ai_system_row_id);
  const aiSystemName =
    aiSystemRow && typeof aiSystemRow.data.name === "string" && aiSystemRow.data.name
      ? aiSystemRow.data.name
      : `AI System #${riskAssessment.ai_system_row_id}`;

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
      />

      <h3>Risk Matrix</h3>
      <RiskMatrix rows={sheet?.rows ?? []} />
    </article>
  );
}
