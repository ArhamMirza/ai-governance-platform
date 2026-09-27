import { useQuery } from "@tanstack/react-query";

import { StatusBadge } from "../../../shared/components/StatusBadge";
import { useServerSyncedText } from "../../../shared/hooks/useServerSyncedText";
import { AuditLogViewer } from "../../audit-log/components/AuditLogViewer";
import { useCanApprove } from "../../audit-log/useCanApprove";
import { DataGrid } from "../../sheets/components/DataGrid";
import { interestedPartiesAdapter, organizationIssuesAdapter } from "../api";
import {
  interestedPartiesKey,
  organizationIssuesKey,
  useApproveOrganizationContext,
  useOrganizationContext,
  useSubmitOrganizationContextForReview,
  useUpdateOrganizationContext,
} from "../hooks";
import { OrganizationContextDraftPanel } from "./OrganizationContextDraftPanel";

const ISSUE_CATEGORY_OPTIONS = [
  { value: "Internal", label: "Internal" },
  { value: "External", label: "External" },
];

const LONG_TEXT_COLUMNS = ["issue", "planned_response", "needs", "expectations", "requirements"];

/** Editing this record after approval withdraws the approval and returns it
 * to draft, the same rule a risk assessment's rows follow -- unlike a
 * Policy, which simply refuses an edit once it's out of draft, this
 * singleton is continuously maintained rather than superseded. */
function ApprovalWithdrawalNotice({ status }: { status: string }) {
  if (status !== "approved") return null;
  return (
    <p className="approval-withdrawal-notice" role="status">
      <strong>Approved.</strong>
      <span>
        Changing the description, the issues or the interested parties withdraws this approval
        and returns it to draft for re-approval.
      </span>
    </p>
  );
}

function NarrativeField({
  id,
  label,
  value,
  placeholder,
  onSave,
}: {
  id: string;
  label: string;
  value: string;
  placeholder: string;
  onSave: (value: string) => void;
}) {
  const [text, setText] = useServerSyncedText(value);
  return (
    <div className="form-field">
      <label htmlFor={id}>{label}</label>
      <textarea
        id={id}
        rows={4}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onBlur={() => text !== value && onSave(text)}
        placeholder={placeholder}
      />
    </div>
  );
}

export function OrganizationContextDetail() {
  const { data: context, isLoading, isError } = useOrganizationContext();
  const updateContext = useUpdateOrganizationContext();
  const submitForReview = useSubmitOrganizationContextForReview();
  const approve = useApproveOrganizationContext();
  const { canApprove, reason } = useCanApprove("OrganizationContext", context?.id ?? 0);

  const issuesQuery = useQuery({
    queryKey: [...organizationIssuesKey],
    queryFn: organizationIssuesAdapter.get,
  });
  const partiesQuery = useQuery({
    queryKey: [...interestedPartiesKey],
    queryFn: interestedPartiesAdapter.get,
  });

  if (isLoading) return <p>Loading context of the organization...</p>;
  if (isError || !context) return <p>Failed to load context of the organization.</p>;

  return (
    <article>
      <div className="page-header">
        <h2>Context of the Organization</h2>
        <StatusBadge status={context.status} />
      </div>
      <p className="page-hint">
        ISO/IEC 42001 Clause 4 -- a description of the organization and its overall use of AI,
        the internal and external issues relevant to it, and its interested parties. Always
        included as background for the chat assistant and every AI drafting feature, whether or
        not a given question would otherwise have found it.
      </p>

      <ApprovalWithdrawalNotice status={context.status} />

      <div className="detail-actions">
        {context.status === "draft" && (
          <button onClick={() => submitForReview.mutate()} disabled={submitForReview.isPending}>
            Submit for Review
          </button>
        )}
        {context.status === "in_review" &&
          (canApprove ? (
            <button onClick={() => approve.mutate()} disabled={approve.isPending}>
              Approve
            </button>
          ) : (
            <p className="approval-note">{reason}</p>
          ))}
      </div>

      <OrganizationContextDraftPanel context={context} />

      <h3>Organization Description and Use of AI</h3>
      <NarrativeField
        id="org-description"
        label="Organization description"
        value={context.organization_description ?? ""}
        placeholder="What the organization is and what it does."
        onSave={(text) =>
          updateContext.mutate({ organization_description: text || null })
        }
      />
      <NarrativeField
        id="ai-usage-overview"
        label="Overall use of AI"
        value={context.ai_usage_overview ?? ""}
        placeholder="How the organization develops, deploys or uses AI overall."
        onSave={(text) => updateContext.mutate({ ai_usage_overview: text || null })}
      />

      <h3>Internal and External Issues</h3>
      <DataGrid
        queryKey={[...organizationIssuesKey]}
        adapter={organizationIssuesAdapter}
        selectOptions={{ category: ISSUE_CATEGORY_OPTIONS }}
        longTextColumnKeys={LONG_TEXT_COLUMNS}
        alsoInvalidate={[["organization-context"], ["audit-log", "OrganizationContext"]]}
      />
      {issuesQuery.isError && <p>Failed to load issues.</p>}

      <h3>Interested Parties</h3>
      <DataGrid
        queryKey={[...interestedPartiesKey]}
        adapter={interestedPartiesAdapter}
        longTextColumnKeys={LONG_TEXT_COLUMNS}
        alsoInvalidate={[["organization-context"], ["audit-log", "OrganizationContext"]]}
      />
      {partiesQuery.isError && <p>Failed to load interested parties.</p>}

      <AuditLogViewer entityType="OrganizationContext" entityId={context.id} />
    </article>
  );
}
