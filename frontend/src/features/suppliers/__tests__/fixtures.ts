import type { SheetWithRows } from "../../sheets/types";
import type { Supplier, SupplierDetail } from "../types";

export function makeSupplier(overrides: Partial<Supplier> = {}): Supplier {
  return {
    id: 1,
    name: "Acme Models",
    supplier_type: "model_provider",
    description: null,
    status: "active",
    owner_id: null,
    contact_name: null,
    contact_email: null,
    contract_reference: null,
    contract_start: null,
    contract_end: null,
    responsibilities: null,
    requirements: null,
    review_interval_months: null,
    first_review_due: null,
    ai_system_row_ids: [],
    next_review_due: null,
    review_overdue: false,
    contract_status: null,
    framework_tags: [],
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

export function makeSupplierDetail(overrides: Partial<SupplierDetail> = {}): SupplierDetail {
  return { ...makeSupplier(), reviews: [], ...overrides };
}

export const aiSystemInventory: SheetWithRows = {
  id: 2,
  entity_type: "AISystemInventory",
  title: "AI System Inventory",
  columns: [{ key: "name", label: "Name", data_type: "text" }],
  rows: [7, 9].map((id, index) => ({
    id,
    sheet_id: 2,
    row_index: index + 1,
    data: { name: id === 7 ? "Resume Screener" : "Fraud Model" },
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  })),
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};
