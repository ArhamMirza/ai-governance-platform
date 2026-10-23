import { useState } from "react";

import { useCurrentUser } from "../../auth/hooks";
import { hasPermission } from "../../auth/permissions";
import { useAiSpend } from "../hooks";

const PERIODS = [7, 30, 90] as const;

/** What each kind of call is, in the words an administrator would use. */
const LABELS: Record<string, string> = {
  assistant: "Assistant answers",
  assistant_retry: "Assistant: retry after a bad citation",
  assistant_query: "Assistant: rewriting a follow-up as a search",
  assistant_summary: "Assistant: summarising a long conversation",
  draft_field: "Impact assessment drafts",
  policy_draft: "Policy drafts",
  policy_draft_retry: "Policy drafts: retry",
  procedure_draft: "Procedure drafts",
  procedure_draft_retry: "Procedure drafts: retry",
  organization_context_draft: "Organization context drafts",
  organization_context_draft_retry: "Organization context drafts: retry",
  risk_item_suggestions: "Risk item suggestions",
  risk_item_suggestions_retry: "Risk item suggestions: retry",
};

function percent(rate: number): string {
  return `${Math.round(rate * 100)}%`;
}

/** Where this deployment's AI tokens go: totals by kind of call, never by
 * person or by topic. The measurement any cost work starts from. */
export function AiSpendPanel() {
  const [days, setDays] = useState<number>(30);
  const { data: me } = useCurrentUser();
  const allowed = hasPermission(me?.role, "manage_settings");
  const { data: report, isLoading, isError } = useAiSpend(days, allowed);

  // Part of how the AI is configured and paid for: administrators only.
  if (!allowed) return null;

  return (
    <section aria-labelledby="ai-spend-heading">
      <h2 id="ai-spend-heading">Where the AI tokens go</h2>
      <div>
        <label htmlFor="spend-period">Period</label>
        <select
          id="spend-period"
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
        >
          {PERIODS.map((period) => (
            <option key={period} value={period}>
              Last {period} days
            </option>
          ))}
        </select>
      </div>
      {isLoading ? (
        <p>Loading usage...</p>
      ) : isError || !report ? (
        <p>Failed to load usage.</p>
      ) : report.calls === 0 ? (
        <p>No AI calls in this period.</p>
      ) : (
        <>
          <dl className="usage-totals">
            <div>
              <dt>Calls</dt>
              <dd>{report.calls.toLocaleString()}</dd>
            </div>
            <div>
              <dt>Tokens sent</dt>
              <dd>{report.prompt_tokens.toLocaleString()}</dd>
            </div>
            <div>
              <dt>Tokens written</dt>
              <dd>{report.completion_tokens.toLocaleString()}</dd>
            </div>
            <div>
              <dt>Sent from a cache</dt>
              <dd>{percent(report.cache_hit_rate)}</dd>
            </div>
          </dl>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Kind of call</th>
                  <th>Calls</th>
                  <th>Average sent</th>
                  <th>Average written</th>
                  <th>Total</th>
                  <th>From a cache</th>
                </tr>
              </thead>
              <tbody>
                {report.by_feature.map((row) => (
                  <tr key={row.feature}>
                    <td>{LABELS[row.feature] ?? row.feature}</td>
                    <td>{row.calls.toLocaleString()}</td>
                    <td>{row.average_prompt_tokens.toLocaleString()}</td>
                    <td>{row.average_completion_tokens.toLocaleString()}</td>
                    <td>
                      {(
                        row.prompt_tokens + row.completion_tokens
                      ).toLocaleString()}
                    </td>
                    <td>{percent(row.cache_hit_rate)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="approval-note">
            “Sent” is what goes to the model; “written” is what it writes back.
            “From a cache” is the part of what was sent that the provider had
            already seen and charges less for. It reads 0% for a provider that
            doesn&rsquo;t report it, as well as when nothing was cached.
          </p>
        </>
      )}
    </section>
  );
}
