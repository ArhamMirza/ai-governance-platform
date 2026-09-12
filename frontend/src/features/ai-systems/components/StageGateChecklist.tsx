import { useState } from "react";

import { readError } from "../../../shared/api/readError";
import {
  useAdvanceStage,
  useArchiveSystem,
  useRevertStage,
  useUploadStageDocument,
} from "../hooks";
import type { AISystemLifecycle } from "../types";

/** Requirement keys that are satisfied by uploading a document -- the key is
 * the document_type the backend looks for, so the control can post it. */
const DOCUMENT_REQUIREMENTS: Record<string, string> = {
  design_document: "design document",
  validation_report: "validation report",
  monitoring_plan: "monitoring plan",
  retirement_signoff: "retirement sign-off",
};

function DocumentUpload({ rowId, documentType }: { rowId: number; documentType: string }) {
  const upload = useUploadStageDocument(rowId);
  const inputId = `stage-doc-${documentType}`;

  return (
    <div className="gate-upload">
      <label htmlFor={inputId}>Upload {DOCUMENT_REQUIREMENTS[documentType]}</label>
      <input
        id={inputId}
        type="file"
        disabled={upload.isPending}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) upload.mutate({ documentType, file });
          e.target.value = "";
        }}
      />
    </div>
  );
}

interface StageGateChecklistProps {
  rowId: number;
  lifecycle: AISystemLifecycle;
}

export function StageGateChecklist({ rowId, lifecycle }: StageGateChecklistProps) {
  const advance = useAdvanceStage(rowId);
  const revert = useRevertStage(rowId);
  const archiveSystem = useArchiveSystem(rowId);
  const [error, setError] = useState<string | null>(null);
  const [revertReason, setRevertReason] = useState("");
  const [showRevert, setShowRevert] = useState(false);

  const handleAdvance = async () => {
    setError(null);
    try {
      await advance.mutateAsync();
    } catch (err) {
      setError(readError(err, "Failed to advance the stage"));
    }
  };

  const handleRevert = async () => {
    setError(null);
    try {
      await revert.mutateAsync(revertReason);
      setShowRevert(false);
      setRevertReason("");
    } catch (err) {
      setError(readError(err, "Failed to move the stage back"));
    }
  };

  const handleArchive = async () => {
    setError(null);
    try {
      await archiveSystem.mutateAsync();
    } catch (err) {
      setError(readError(err, "Failed to archive this system"));
    }
  };

  const isFinalStage = lifecycle.next_stage === null;

  if (lifecycle.is_archived) {
    return (
      <div className="stage-gate">
        <h3>Archived</h3>
        <p>
          Retired{lifecycle.retired_at ? ` on ${lifecycle.retired_at}` : ""}. This record is
          kept until {lifecycle.retention_until ?? "—"}
          {lifecycle.retention_expired
            ? " — the retention period has passed, so it can now be deleted."
            : " and cannot be deleted before then."}
        </p>
      </div>
    );
  }

  return (
    <div className="stage-gate">
      <h3>
        {isFinalStage
          ? "To archive this system"
          : `To leave ${lifecycle.current_stage_label}`}
      </h3>

      {error && <p role="alert">{error}</p>}

      {lifecycle.requirements.length === 0 && !isFinalStage && (
        <p>No requirements outstanding for this stage.</p>
      )}

      <ul className="gate-requirements">
        {lifecycle.requirements.map((requirement) => (
          <li
            key={requirement.key}
            className={requirement.satisfied ? "is-satisfied" : "is-unsatisfied"}
          >
            <span className="gate-marker" aria-hidden="true">
              {requirement.satisfied ? "✓" : "○"}
            </span>
            <span>
              <strong>{requirement.label}</strong>
              <span className="gate-detail">{requirement.detail}</span>
              {!requirement.satisfied && DOCUMENT_REQUIREMENTS[requirement.key] && (
                <DocumentUpload rowId={rowId} documentType={requirement.key} />
              )}
            </span>
          </li>
        ))}
      </ul>

      <div className="stage-gate-actions">
        {isFinalStage ? (
          <button
            type="submit"
            onClick={handleArchive}
            disabled={!lifecycle.can_archive || archiveSystem.isPending}
          >
            {archiveSystem.isPending ? "Archiving..." : "Complete retirement & archive"}
          </button>
        ) : (
          <button
            type="submit"
            onClick={handleAdvance}
            disabled={!lifecycle.can_advance || advance.isPending}
          >
            {advance.isPending
              ? "Advancing..."
              : `Advance to ${lifecycle.next_stage_label}`}
          </button>
        )}
        <button onClick={() => setShowRevert((prev) => !prev)}>
          {showRevert ? "Cancel" : "Move back a stage"}
        </button>
      </div>

      {showRevert && (
        <div className="stage-revert">
          <label htmlFor="stage-revert-reason">Why is this system moving back?</label>
          <textarea
            id="stage-revert-reason"
            rows={2}
            value={revertReason}
            onChange={(e) => setRevertReason(e.target.value)}
          />
          <button onClick={handleRevert} disabled={!revertReason.trim() || revert.isPending}>
            {revert.isPending ? "Moving back..." : "Confirm move back"}
          </button>
        </div>
      )}
    </div>
  );
}
