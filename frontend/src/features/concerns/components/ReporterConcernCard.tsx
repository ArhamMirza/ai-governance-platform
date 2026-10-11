import { StatusBadge } from "../../../shared/components/StatusBadge";
import { categoryLabel, outcomeLabel, reporterStatusLabel } from "../labels";
import type { ReporterConcern } from "../types";

/** One concern as the person who raised it sees it: what they said, where it
 * stands, and the reply -- never anything the handler wrote privately. */
export function ReporterConcernCard({ concern }: { concern: ReporterConcern }) {
  return (
    <article className="reporter-concern">
      <header className="record-header-top">
        <h3>{categoryLabel(concern.category)}</h3>
        <StatusBadge status={concern.status} />
        <span className="approval-note">{reporterStatusLabel(concern.status)}</span>
      </header>
      <p className="approval-note">
        Raised {concern.received_on}
        {concern.is_anonymous && " · anonymously"}
        {concern.acknowledged_on && ` · acknowledged ${concern.acknowledged_on}`}
        {concern.closed_on && ` · closed ${concern.closed_on}`}
      </p>
      <p>{concern.description}</p>
      {concern.outcome && <p>Outcome: {outcomeLabel(concern.outcome)}</p>}
      {concern.reply_to_reporter ? (
        <blockquote>{concern.reply_to_reporter}</blockquote>
      ) : (
        <p className="approval-note">No reply yet.</p>
      )}
    </article>
  );
}
