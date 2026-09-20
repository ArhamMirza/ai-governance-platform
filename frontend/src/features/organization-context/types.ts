export type OrganizationContextStatus = "draft" | "in_review" | "approved";

export interface OrganizationContext {
  id: number;
  organization_description: string | null;
  ai_usage_overview: string | null;
  status: OrganizationContextStatus;
  approved_by: number | null;
  approved_at: string | null;
  next_review_date: string | null;
  created_at: string;
  updated_at: string;
}

/** Only the fields being changed -- a save of one narrative field must not
 * send the other and blank it out server-side (organization_context_service
 * .update treats a key's absence as "leave it alone", not "clear it"). */
export interface OrganizationContextUpdateInput {
  organization_description?: string | null;
  ai_usage_overview?: string | null;
}
