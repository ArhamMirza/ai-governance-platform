import { Link } from "react-router-dom";

import { AuditLogViewer } from "../../audit-log/components/AuditLogViewer";
import { useAISystemInventoryRows } from "../../ai-system-inventory/hooks";
import { DocumentBrowser } from "../../evidence/components/DocumentBrowser";
import { useAllImpactAssessments } from "../../impact-assessments/hooks";
import { useRiskAssessments } from "../../risk-assessments/hooks";
import { AISystemObjectives } from "../../objectives/components/AISystemObjectives";
import { AISystemSuppliers } from "../../suppliers/components/AISystemSuppliers";
import { useLifecycle } from "../hooks";
import { LifecycleStageTracker } from "./LifecycleStageTracker";
import {
  DeploymentRecordFields,
  MonitoringFields,
  OwnerField,
  RetirementFields,
} from "./StageFields";
import { StageGateChecklist } from "./StageGateChecklist";

const ENTITY_TYPE = "AISystem";

interface AISystemDetailProps {
  rowId: number;
}

export function AISystemDetail({ rowId }: AISystemDetailProps) {
  const { data: lifecycle, isLoading, isError } = useLifecycle(rowId);
  const { data: inventory } = useAISystemInventoryRows();
  const { data: impactAssessments } = useAllImpactAssessments();
  const { data: riskAssessments } = useRiskAssessments();

  if (isLoading) return <p>Loading AI system...</p>;
  if (isError || !lifecycle) return <p>Failed to load this AI system.</p>;

  const row = inventory?.rows.find((r) => r.id === rowId);
  const name =
    row && typeof row.data.name === "string" && row.data.name
      ? row.data.name
      : `AI System #${rowId}`;

  const impact = (impactAssessments ?? []).find((a) => a.ai_system_row_id === rowId);
  const risk = (riskAssessments ?? []).find((r) => r.ai_system_row_id === rowId);

  return (
    <article>
      <div className="page-header">
        <div>
          <h1>{name}</h1>
          <p>
            {lifecycle.current_stage_label} since{" "}
            {new Date(lifecycle.entered_stage_at).toLocaleDateString()}
          </p>
        </div>
      </div>

      <LifecycleStageTracker currentStage={lifecycle.current_stage} />

      <OwnerField rowId={rowId} lifecycle={lifecycle} />

      <StageGateChecklist rowId={rowId} lifecycle={lifecycle} />

      {/* Shown from V&V onwards -- that's the gate these facts feed. */}
      {["verification_and_validation", "deployment", "operation_and_monitoring", "retirement"].includes(
        lifecycle.current_stage,
      ) && <DeploymentRecordFields rowId={rowId} lifecycle={lifecycle} />}

      {["deployment", "operation_and_monitoring", "retirement"].includes(
        lifecycle.current_stage,
      ) && <MonitoringFields rowId={rowId} lifecycle={lifecycle} />}

      {/* Retirement is decided during Operation & Monitoring, so the fields
          appear a stage before they gate anything. */}
      {["operation_and_monitoring", "retirement"].includes(lifecycle.current_stage) && (
        <RetirementFields rowId={rowId} lifecycle={lifecycle} />
      )}

      <h3>Assessments</h3>
      <ul className="assessment-links">
        <li>
          {impact ? (
            <Link to={`/impact-assessments/${impact.id}`}>
              Impact assessment — {impact.status}
            </Link>
          ) : (
            <span className="framework-tags-empty">
              No impact assessment yet. Start one from Impact &amp; Risk Assessments.
            </span>
          )}
        </li>
        <li>
          {risk ? (
            <Link to={`/risk-assessments/${risk.id}`}>Risk assessment — {risk.status}</Link>
          ) : (
            <span className="framework-tags-empty">No risk assessment yet.</span>
          )}
        </li>
      </ul>

      <h3>Suppliers</h3>
      <AISystemSuppliers rowId={rowId} />

      <h3>AI Objectives</h3>
      <AISystemObjectives rowId={rowId} />

      <h3>Documents</h3>
      <DocumentBrowser entityType={ENTITY_TYPE} entityId={rowId} />

      <AuditLogViewer entityType={ENTITY_TYPE} entityId={rowId} />
    </article>
  );
}
