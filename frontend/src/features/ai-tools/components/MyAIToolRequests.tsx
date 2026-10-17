import { useMyAIToolRequests } from "../hooks";
import { AIToolStatusBadge } from "./AIToolStatusBadge";

/** An employee's own requests for tools, and how each was answered. */
export function MyAIToolRequests() {
  const { data: requests, isLoading, isError } = useMyAIToolRequests();

  if (isLoading) return <p>Loading your requests...</p>;
  if (isError) return <p>Failed to load your requests.</p>;
  if (!requests || requests.length === 0) return <p>You haven't asked for any tools.</p>;

  return (
    <ul className="plain-list">
      {requests.map((request) => (
        <li key={request.id} className="reporter-concern">
          <p>
            <strong>{request.tool_name}</strong> <AIToolStatusBadge status={request.status} />
          </p>
          <p className="approval-note">Asked {request.requested_on}</p>
          <blockquote>{request.purpose}</blockquote>
          {request.decided_on && (
            <p>
              Answered {request.decided_on}
              {request.decision_note && `: ${request.decision_note}`}
            </p>
          )}
        </li>
      ))}
    </ul>
  );
}
