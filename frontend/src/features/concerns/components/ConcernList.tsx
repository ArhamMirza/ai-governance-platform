import { useState } from "react";
import { Link } from "react-router-dom";

import { StatusBadge } from "../../../shared/components/StatusBadge";
import { useConcerns } from "../hooks";
import { categoryLabel, channelLabel } from "../labels";
import type { ConcernStatus } from "../types";

type Filter = "open" | "all" | ConcernStatus;

const FILTERS: { value: Filter; label: string }[] = [
  { value: "open", label: "Open" },
  { value: "received", label: "Not yet acknowledged" },
  { value: "under_review", label: "Being looked into" },
  { value: "resolved", label: "Resolved" },
  { value: "not_actioned", label: "Closed without action" },
  { value: "all", label: "All" },
];

export function ConcernList() {
  const { data: concerns, isLoading, isError } = useConcerns();
  const [filter, setFilter] = useState<Filter>("open");

  if (isLoading) return <p>Loading concerns...</p>;
  if (isError) return <p>Failed to load concerns.</p>;

  const shown = (concerns ?? []).filter((concern) => {
    if (filter === "all") return true;
    if (filter === "open") return concern.status === "received" || concern.status === "under_review";
    return concern.status === filter;
  });

  return (
    <div>
      <div>
        <label htmlFor="concern-filter">Show</label>
        <select
          id="concern-filter"
          value={filter}
          onChange={(e) => setFilter(e.target.value as Filter)}
        >
          {FILTERS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
      {shown.length === 0 ? (
        <p>No concerns here.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Concern</th>
              <th>About</th>
              <th>Received</th>
              <th>Status</th>
              <th>Acknowledge by</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((concern) => (
              <tr key={concern.id} className={concern.awaiting_triage ? "row-flagged" : undefined}>
                <td>
                  <Link to={`/concerns/${concern.id}`}>
                    {concern.description.length > 70
                      ? `${concern.description.slice(0, 70)}…`
                      : concern.description}
                  </Link>
                  {concern.awaiting_triage && <span className="flag-chip">Not acknowledged</span>}
                </td>
                <td>{categoryLabel(concern.category)}</td>
                <td data-type="date">
                  {concern.received_on}{" "}
                  <span className="approval-note">
                    {channelLabel(concern.channel)}
                    {concern.is_anonymous && " · anonymous"}
                  </span>
                </td>
                <td>
                  <StatusBadge status={concern.status} />
                </td>
                <td data-type="date">
                  {concern.status === "received" ? concern.acknowledge_by : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
