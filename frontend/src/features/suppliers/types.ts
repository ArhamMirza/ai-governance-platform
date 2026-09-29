import type { FrameworkControl } from "../framework-controls/types";

export type SupplierType =
  | "model_provider"
  | "data_provider"
  | "infrastructure"
  | "software"
  | "services"
  | "other";
export type SupplierStatus = "active" | "inactive";
export type SupplierReviewOutcome = "satisfactory" | "concerns" | "unsatisfactory";
export type ContractStatus = "expired" | "expiring";

export interface SupplierReview {
  id: number;
  supplier_id: number;
  review_date: string;
  outcome: SupplierReviewOutcome;
  notes: string | null;
  reviewed_by: number | null;
  created_at: string;
}

export interface Supplier {
  id: number;
  name: string;
  supplier_type: SupplierType;
  description: string | null;
  status: SupplierStatus;
  owner_id: number | null;
  contact_name: string | null;
  contact_email: string | null;
  contract_reference: string | null;
  contract_start: string | null;
  contract_end: string | null;
  responsibilities: string | null;
  requirements: string | null;
  review_interval_months: number | null;
  first_review_due: string | null;
  ai_system_row_ids: number[];
  next_review_due: string | null;
  review_overdue: boolean;
  contract_status: ContractStatus | null;
  framework_tags: FrameworkControl[];
  created_at: string;
  updated_at: string;
}

export interface SupplierDetail extends Supplier {
  reviews: SupplierReview[];
}

export interface SupplierCreateInput {
  name: string;
  supplier_type?: SupplierType;
  description?: string | null;
  owner_id?: number | null;
  contract_reference?: string | null;
  contract_start?: string | null;
  contract_end?: string | null;
}

export type SupplierUpdateInput = Partial<
  Omit<
    Supplier,
    | "id"
    | "ai_system_row_ids"
    | "next_review_due"
    | "review_overdue"
    | "contract_status"
    | "framework_tags"
    | "created_at"
    | "updated_at"
  >
>;

export interface SupplierReviewInput {
  review_date: string;
  outcome: SupplierReviewOutcome;
  notes?: string | null;
}
