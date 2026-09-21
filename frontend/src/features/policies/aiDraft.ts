import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { httpClient } from "../../shared/api/httpClient";
import { policiesKey, policyAuditLogKey, policyKey } from "./hooks";
import type { Policy } from "./types";

/** One field the model proposed for the policy. */
export interface PolicyDraftProposal {
  key: string;
  section: string;
  field: string;
  label: string;
  value: string | null;
  citations: number[];
  /** What the records were missing, where they didn't support drafting it. */
  gap: string | null;
  /** Proposed without citing any source: shown, but flagged for scrutiny. */
  uncited: boolean;
  /** Every source it cited was invented, so no text is offered at all. */
  withheld: boolean;
}

export interface PolicyDraftSource {
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

export interface PolicyDraft {
  id: number;
  status: string;
  provider: string;
  model: string;
  requested_by: number | null;
  created_at: string;
  proposals: PolicyDraftProposal[];
  sources: PolicyDraftSource[];
  injection_findings: string[] | null;
  coverage_gaps: { evidence_id: number; filename: string; detail: string | null }[] | null;
}

export interface AcceptedPolicyField {
  key: string;
  value: string;
}

const base = (policyId: number) => `/policies/${policyId}/ai-draft`;

export const policyDraftApi = {
  generate: (policyId: number, instructions?: string) =>
    httpClient.post<PolicyDraft>(base(policyId), { instructions: instructions || null }),
  latest: (policyId: number) => httpClient.get<PolicyDraft | null>(`${base(policyId)}/latest`),
  apply: (policyId: number, draftId: number, accepted: AcceptedPolicyField[]) =>
    httpClient.post<Policy>(`${base(policyId)}/${draftId}/apply`, { accepted }),
  discard: (policyId: number, draftId: number) =>
    httpClient.post<void>(`${base(policyId)}/${draftId}/discard`),
};

const draftKey = (policyId: number) => [...policyKey(policyId), "ai-draft"] as const;

/** The draft still waiting for a decision. Survives a page reload, so a
 * long review isn't lost to navigating away. */
export function useLatestPolicyDraft(policyId: number, enabled: boolean) {
  return useQuery({
    queryKey: draftKey(policyId),
    queryFn: () => policyDraftApi.latest(policyId),
    enabled,
  });
}

export function useGeneratePolicyDraft(policyId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (instructions?: string) => policyDraftApi.generate(policyId, instructions),
    onSuccess: (draft) => queryClient.setQueryData(draftKey(policyId), draft),
  });
}

export function useApplyPolicyDraft(policyId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ draftId, accepted }: { draftId: number; accepted: AcceptedPolicyField[] }) =>
      policyDraftApi.apply(policyId, draftId, accepted),
    onSuccess: () => {
      queryClient.setQueryData(draftKey(policyId), null);
      // Applying writes through the same path as editing by hand -- refresh
      // everything an edit would.
      queryClient.invalidateQueries({ queryKey: policiesKey });
      queryClient.invalidateQueries({ queryKey: policyKey(policyId) });
      queryClient.invalidateQueries({ queryKey: policyAuditLogKey(policyId) });
    },
  });
}

export function useDiscardPolicyDraft(policyId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (draftId: number) => policyDraftApi.discard(policyId, draftId),
    onSuccess: () => queryClient.setQueryData(draftKey(policyId), null),
  });
}
