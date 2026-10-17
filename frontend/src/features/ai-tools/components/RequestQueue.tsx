import { useState } from "react";
import { Link } from "react-router-dom";

import { readError } from "../../../shared/api/readError";
import { useUserDirectory } from "../../users/hooks";
import { useAIToolRequests, useDecideAIToolRequest } from "../hooks";
import { CLASSIFICATION_OPTIONS } from "../labels";
import type { AIToolRequest, DataClassification } from "../types";
import { AIToolStatusBadge } from "./AIToolStatusBadge";

/** One request, with the form for answering it when it is still waiting. */
function RequestRow({ request, requester }: { request: AIToolRequest; requester: string }) {
  const decide = useDecideAIToolRequest();
  const open = request.status === "requested";
  // A request for a tool already in the catalogue, or one that gave an
  // address, needs no address from the person answering it.
  const needsDomain = open && request.tool_id === null && request.domain === null;
  const [classification, setClassification] = useState<DataClassification>("internal");
  const [conditions, setConditions] = useState("");
  const [domain, setDomain] = useState("");
  const [note, setNote] = useState("");

  const answer = (action: "approve" | "reject") =>
    decide.mutate({
      id: request.id,
      data: {
        action,
        domain: action === "approve" && domain.trim() ? domain.trim() : null,
        max_data_classification: action === "approve" ? classification : null,
        conditions_of_use: action === "approve" ? conditions.trim() || null : null,
        review_due: null,
        note: note.trim() || null,
      },
    });

  return (
    <li className="reporter-concern">
      <p>
        <strong>{request.tool_name}</strong> <AIToolStatusBadge status={request.status} />{" "}
        {request.tool_id !== null && <Link to={`/ai-tools/${request.tool_id}`}>View tool</Link>}
      </p>
      <p className="approval-note">
        Asked by {requester} on {request.requested_on}
        {request.domain && ` · ${request.domain}`}
      </p>
      <blockquote>{request.purpose}</blockquote>
      {request.data_involved && <p>Data it would touch: {request.data_involved}</p>}
      {request.decided_on && (
        <p>
          Answered {request.decided_on}
          {request.decision_note && `: ${request.decision_note}`}
        </p>
      )}
      {open && (
        <div>
          {needsDomain && (
            <div>
              <label htmlFor={`request-domain-${request.id}`}>Address to allow</label>
              <input
                id={`request-domain-${request.id}`}
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
              />
            </div>
          )}
          <div>
            <label htmlFor={`request-class-${request.id}`}>
              Most sensitive data it may be given
            </label>
            <select
              id={`request-class-${request.id}`}
              value={classification}
              onChange={(e) => setClassification(e.target.value as DataClassification)}
            >
              {CLASSIFICATION_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor={`request-conditions-${request.id}`}>Conditions of use</label>
            <input
              id={`request-conditions-${request.id}`}
              value={conditions}
              onChange={(e) => setConditions(e.target.value)}
            />
          </div>
          <div>
            <label htmlFor={`request-note-${request.id}`}>
              Note to the employee (needed to say no)
            </label>
            <input
              id={`request-note-${request.id}`}
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </div>
          <div className="detail-actions">
            <button
              onClick={() => answer("approve")}
              disabled={decide.isPending || (needsDomain && !domain.trim())}
            >
              Approve {request.tool_name}
            </button>
            <button onClick={() => answer("reject")} disabled={decide.isPending || !note.trim()}>
              Say No
            </button>
          </div>
          {decide.isError && (
            <p role="alert">{readError(decide.error, "Failed to answer the request.")}</p>
          )}
        </div>
      )}
    </li>
  );
}

/** Requests from employees for tools to be allowed. Waiting ones come first
 * and are shown in full; answered ones stay below as the record. */
export function RequestQueue() {
  const { data: requests, isLoading, isError } = useAIToolRequests();
  const { data: directory } = useUserDirectory();

  if (isLoading) return <p>Loading requests...</p>;
  if (isError) return <p>Failed to load requests.</p>;
  if (!requests || requests.length === 0) return <p>No one has asked for a tool yet.</p>;

  const nameOf = (id: number) => directory?.find((user) => user.id === id)?.name ?? `User #${id}`;
  const waiting = requests.filter((request) => request.status === "requested");
  const answered = requests.filter((request) => request.status !== "requested");

  return (
    <>
      <h3>Waiting for a decision ({waiting.length})</h3>
      {waiting.length === 0 ? (
        <p>Nothing is waiting.</p>
      ) : (
        <ul className="plain-list">
          {waiting.map((request) => (
            <RequestRow key={request.id} request={request} requester={nameOf(request.requester_id)} />
          ))}
        </ul>
      )}
      {answered.length > 0 && (
        <>
          <h3>Answered</h3>
          <ul className="plain-list">
            {answered.map((request) => (
              <RequestRow
                key={request.id}
                request={request}
                requester={nameOf(request.requester_id)}
              />
            ))}
          </ul>
        </>
      )}
    </>
  );
}
