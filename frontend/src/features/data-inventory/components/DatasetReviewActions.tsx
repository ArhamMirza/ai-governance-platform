import { useState } from "react";

import { readError } from "../../../shared/api/readError";
import { useCurrentUser } from "../../auth/hooks";
import { useCanApprove } from "../../audit-log/useCanApprove";
import type { SheetRow } from "../../sheets/types";
import { useApproveDataset, useSubmitDatasetForApproval } from "../hooks";

const APPROVAL_ENTITY_TYPE = "DataInventoryApproval";

function statusOf(row: SheetRow): string {
  return String(row.data.approval_status ?? "draft");
}

function isDataOwner(row: SheetRow, userId: number | undefined, role: string | undefined) {
  if (userId === undefined) return false;
  if (role === "admin") return true;
  const owner = String(row.data.data_owner ?? "").trim();
  // An unowned dataset is open to whoever is filling it in, matching the
  // backend's _require_data_owner.
  return owner === "" || owner === String(userId);
}

/** Only rendered for a dataset awaiting sign-off, so the audit-log lookup
 * behind useCanApprove doesn't fire once per row of the whole grid. */
function ApproveAction({ row }: { row: SheetRow }) {
  const { canApprove, reason } = useCanApprove(APPROVAL_ENTITY_TYPE, row.id);
  const approve = useApproveDataset();
  const [error, setError] = useState<string | null>(null);

  if (!canApprove) return <span className="framework-tags-empty">{reason}</span>;

  return (
    <>
      {error && <span role="alert">{error}</span>}
      <button
        disabled={approve.isPending}
        onClick={async () => {
          setError(null);
          try {
            await approve.mutateAsync(row.id);
          } catch (err) {
            setError(readError(err, "Failed to approve this dataset"));
          }
        }}
      >
        Approve
      </button>
    </>
  );
}

function SubmitAction({ row }: { row: SheetRow }) {
  const submit = useSubmitDatasetForApproval();
  const [error, setError] = useState<string | null>(null);

  return (
    <>
      {error && <span role="alert">{error}</span>}
      <button
        disabled={submit.isPending}
        onClick={async () => {
          setError(null);
          try {
            await submit.mutateAsync(row.id);
          } catch (err) {
            setError(readError(err, "Failed to submit this dataset"));
          }
        }}
      >
        Submit for approval
      </button>
    </>
  );
}

export function DatasetReviewActions({ row }: { row: SheetRow }) {
  const { data: me } = useCurrentUser();
  const status = statusOf(row);

  if (status === "pending_approval") return <ApproveAction row={row} />;
  if (status === "approved") return null;
  if (!isDataOwner(row, me?.id, me?.role)) return null;
  return <SubmitAction row={row} />;
}
