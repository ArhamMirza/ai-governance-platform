export type DataInventoryStatus = "draft" | "pending_approval" | "approved";

export interface DataInventoryRecord {
  data_inventory_row_id: number;
  status: DataInventoryStatus;
  submitted_by: number | null;
  submitted_by_name: string | null;
  submitted_at: string | null;
  approved_by: number | null;
  approved_by_name: string | null;
  approved_at: string | null;
}

export const STATUS_LABELS: Record<DataInventoryStatus, string> = {
  draft: "Draft",
  pending_approval: "Pending approval",
  approved: "Approved",
};
