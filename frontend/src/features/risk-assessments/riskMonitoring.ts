import type { SheetRow } from "../sheets/types";

// Free-text status values treated as "no longer outstanding" for overdue
// purposes -- the status column has no enforced set of values, so this is a
// best-effort match rather than a strict enum.
const TREATED_STATUSES = new Set([
  "treated",
  "closed",
  "resolved",
  "completed",
  "done",
  "mitigated",
]);

export function isRiskItemOverdue(row: SheetRow, now: Date = new Date()): boolean {
  const deadline = row.data.treatment_deadline;
  if (typeof deadline !== "string" || !deadline) return false;

  const deadlineDate = new Date(deadline);
  if (Number.isNaN(deadlineDate.getTime())) return false;

  const status = typeof row.data.status === "string" ? row.data.status.trim().toLowerCase() : "";
  if (TREATED_STATUSES.has(status)) return false;

  return deadlineDate.getTime() < now.getTime();
}
