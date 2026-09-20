import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { httpClient } from "../../shared/api/httpClient";
import { interestedPartiesKey, organizationIssuesKey } from "./hooks";
import type { OrganizationContext } from "./types";

/** One thing the model proposed -- a narrative field, an issue, or an
 * interested party -- not yet saved. */
export interface ContextProposal {
  key: string;
  kind: "narrative" | "issue" | "party";
  field: string | null;
  label: string | null;
  value: string | null;
  category: string | null;
  issue: string | null;
  planned_response: string | null;
  party: string | null;
  needs: string | null;
  expectations: string | null;
  requirements: string | null;
  citations: number[];
  /** What the records were missing, where they didn't support proposing it. */
  gap: string | null;
  /** Proposed without citing any source: shown, but flagged for scrutiny. */
  uncited: boolean;
  /** Every source it cited was invented, or it had no content at all. */
  withheld: boolean;
}

export interface ContextDraftSource {
  n: number;
  title: string;
  section: string | null;
  kind: string;
  href: string | null;
  download_evidence_id: number | null;
  read_by_ocr: boolean;
  excerpt: string;
  injection_findings: string[];
}

export interface OrganizationContextDraft {
  id: number;
  status: string;
  provider: string;
  model: string;
  requested_by: number | null;
  created_at: string;
  proposals: ContextProposal[];
  sources: ContextDraftSource[];
  injection_findings: string[] | null;
  coverage_gaps: { evidence_id: number; filename: string; detail: string | null }[] | null;
}

export interface AcceptedNarrativeField {
  key: string;
  value: string;
}

export interface AcceptedIssueRow {
  key: string;
  category: string;
  issue: string;
  planned_response?: string | null;
}

export interface AcceptedInterestedParty {
  key: string;
  party: string;
  needs?: string | null;
  expectations?: string | null;
  requirements?: string | null;
}

export interface AcceptedContextDraft {
  narrative: AcceptedNarrativeField[];
  issues: AcceptedIssueRow[];
  interested_parties: AcceptedInterestedParty[];
}

const BASE = "/organization-context/ai-draft";

export const organizationContextDraftApi = {
  generate: () => httpClient.post<OrganizationContextDraft>(BASE),
  latest: () => httpClient.get<OrganizationContextDraft | null>(`${BASE}/latest`),
  apply: (draftId: number, accepted: AcceptedContextDraft) =>
    httpClient.post<OrganizationContext>(`${BASE}/${draftId}/apply`, accepted),
  discard: (draftId: number) => httpClient.post<void>(`${BASE}/${draftId}/discard`),
};

const draftKey = ["organization-context", "ai-draft"] as const;

/** The draft still waiting for a decision. Survives a page reload, so a
 * long review isn't lost to navigating away. */
export function useLatestOrganizationContextDraft(enabled: boolean) {
  return useQuery({
    queryKey: draftKey,
    queryFn: organizationContextDraftApi.latest,
    enabled,
  });
}

export function useGenerateOrganizationContextDraft() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => organizationContextDraftApi.generate(),
    onSuccess: (draft) => queryClient.setQueryData(draftKey, draft),
  });
}

export function useApplyOrganizationContextDraft() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ draftId, accepted }: { draftId: number; accepted: AcceptedContextDraft }) =>
      organizationContextDraftApi.apply(draftId, accepted),
    onSuccess: () => {
      queryClient.setQueryData(draftKey, null);
      // Applying writes through the same paths as editing by hand, and can
      // withdraw the approval -- refresh everything an edit would.
      queryClient.invalidateQueries({ queryKey: ["organization-context"] });
      queryClient.invalidateQueries({ queryKey: [...organizationIssuesKey] });
      queryClient.invalidateQueries({ queryKey: [...interestedPartiesKey] });
      queryClient.invalidateQueries({ queryKey: ["audit-log", "OrganizationContext"] });
    },
  });
}

export function useDiscardOrganizationContextDraft() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (draftId: number) => organizationContextDraftApi.discard(draftId),
    onSuccess: () => queryClient.setQueryData(draftKey, null),
  });
}
