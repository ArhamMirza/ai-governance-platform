import { useState } from "react";
import { Link } from "react-router-dom";

import { readError } from "../../../shared/api/readError";
import { ConfirmDialog } from "../../../shared/components/ConfirmDialog";
import { useDeleteInventoryRow } from "../../ai-system-inventory/hooks";
import { useArchivedSystems } from "../hooks";
import type { ArchivedAISystem } from "../types";

export function ArchiveTable() {
  const { data: archived, isLoading, isError } = useArchivedSystems();
  const deleteRow = useDeleteInventoryRow();
  const [pendingDelete, setPendingDelete] = useState<ArchivedAISystem | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (isLoading) return <p>Loading the archive...</p>;
  if (isError || !archived) return <p>Failed to load the archive.</p>;
  if (archived.length === 0) {
    return <p>Nothing archived yet. Retired AI systems are kept here.</p>;
  }

  const handleDelete = async () => {
    if (!pendingDelete) return;
    setError(null);
    try {
      await deleteRow.mutateAsync(pendingDelete.ai_system_row_id);
      setPendingDelete(null);
    } catch (err) {
      setError(readError(err, "Failed to delete this record"));
    }
  };

  return (
    <>
      {error && !pendingDelete && <p role="alert">{error}</p>}

      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>AI System</th>
              <th>Retired</th>
              <th>Reason</th>
              <th>Retention</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {archived.map((entry) => (
              <tr key={entry.ai_system_row_id}>
                <td>
                  <Link to={`/ai-systems/${entry.ai_system_row_id}`}>{entry.name}</Link>
                </td>
                <td>{entry.retired_at ?? "—"}</td>
                <td>{entry.retirement_reason ?? "—"}</td>
                <td>
                  <span
                    className={`impact-review-chip${entry.retention_expired ? " is-overdue" : ""}`}
                  >
                    {entry.retention_expired ? "Expired" : "Kept until"}{" "}
                    {entry.retention_until ?? "—"}
                  </span>
                </td>
                <td>
                  {entry.retention_expired ? (
                    <button onClick={() => setPendingDelete(entry)}>Delete permanently</button>
                  ) : (
                    <span className="framework-tags-empty">
                      Can&apos;t be deleted until retention ends.
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {pendingDelete && (
        <ConfirmDialog
          title="Delete this record permanently?"
          message={`This erases everything kept for ${pendingDelete.name} — its assessments, evidence and audit trail. Its retention period ended on ${pendingDelete.retention_until}. This cannot be undone.`}
          confirmLabel="Delete permanently"
          isPending={deleteRow.isPending}
          error={error}
          onCancel={() => {
            setPendingDelete(null);
            setError(null);
          }}
          onConfirm={handleDelete}
        />
      )}
    </>
  );
}
