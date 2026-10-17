import { STATUS_LABELS } from "../labels";
import type { AIToolRequestStatus, AIToolStatus } from "../types";

const REQUEST_LABELS: Record<AIToolRequestStatus, string> = {
  requested: "Waiting for a decision",
  approved: "Approved",
  rejected: "Not approved",
};

/** A tool's standing, or a request's outcome, in plain words -- the shared
 * badge would print the raw status ("catalogued"). */
export function AIToolStatusBadge({ status }: { status: AIToolStatus | AIToolRequestStatus }) {
  const label =
    status in STATUS_LABELS
      ? STATUS_LABELS[status as AIToolStatus]
      : REQUEST_LABELS[status as AIToolRequestStatus];
  return (
    <span className="status-badge" data-status={status}>
      {label}
    </span>
  );
}
