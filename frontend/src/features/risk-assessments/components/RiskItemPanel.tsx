import { readError } from "../../../shared/api/readError";
import { useEvidenceList } from "../../evidence/hooks";
import { DocumentBrowser } from "../../evidence/components/DocumentBrowser";
import { useCloseRiskItem } from "../hooks";
import type { SheetRow } from "../../sheets/types";

const RISK_ITEM_ENTITY_TYPE = "RiskItem";

interface RiskItemPanelProps {
  riskAssessmentId: number;
  row: SheetRow;
  onClose: () => void;
}

export function RiskItemPanel({ riskAssessmentId, row, onClose }: RiskItemPanelProps) {
  const { data: evidence } = useEvidenceList(RISK_ITEM_ENTITY_TYPE, row.id, null);
  const closeRiskItem = useCloseRiskItem(riskAssessmentId);

  const isClosed = row.data.status === "closed";
  const hasEvidence = (evidence?.length ?? 0) > 0;

  const handleClose = async () => {
    try {
      await closeRiskItem.mutateAsync(row.id);
    } catch {
      // Surfaced below via closeRiskItem.error
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-panel" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <h3>{typeof row.data.category === "string" ? row.data.category : "Risk Item"}</h3>
            {typeof row.data.description === "string" && row.data.description && (
              <p>{row.data.description}</p>
            )}
          </div>
          <button onClick={onClose} aria-label="Close panel">
            ×
          </button>
        </div>

        {isClosed ? (
          <p className="approval-note">
            This risk item is closed
            {typeof row.data.closed_at === "string"
              ? ` (${new Date(row.data.closed_at).toLocaleString()})`
              : ""}
            .
          </p>
        ) : (
          <>
            <h4>Evidence</h4>
            <DocumentBrowser entityType={RISK_ITEM_ENTITY_TYPE} entityId={row.id} />

            {closeRiskItem.isError && (
              <p role="alert">{readError(closeRiskItem.error, "Failed to close risk item")}</p>
            )}

            {hasEvidence ? (
              <button onClick={handleClose} disabled={closeRiskItem.isPending}>
                {closeRiskItem.isPending ? "Closing..." : "Mark Risk Closed"}
              </button>
            ) : (
              <p className="approval-note">
                Attach at least one piece of evidence before this risk item can be closed.
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
