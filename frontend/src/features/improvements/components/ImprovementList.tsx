import { useState } from "react";
import { Link } from "react-router-dom";

import { StatusBadge } from "../../../shared/components/StatusBadge";
import { useImprovements } from "../hooks";
import { sourceLabel } from "../labels";
import type { Improvement, ImprovementStatus } from "../types";

/** The chip an improvement carries wherever it's listed. */
export function ImprovementFlags({ improvement }: { improvement: Improvement }) {
  return improvement.standing.overdue ? <span className="flag-chip">Overdue</span> : null;
}

type Filter = "open" | "all" | ImprovementStatus;

const FILTERS: { value: Filter; label: string }[] = [
  { value: "open", label: "Open" },
  { value: "proposed", label: "Proposed" },
  { value: "accepted", label: "Accepted" },
  { value: "implemented", label: "Implemented" },
  { value: "declined", label: "Declined" },
  { value: "all", label: "All" },
];

function matches(improvement: Improvement, filter: Filter): boolean {
  const state = improvement.standing.state;
  if (filter === "all") return true;
  if (filter === "open") return state === "proposed" || state === "accepted";
  return state === filter;
}

export function ImprovementList() {
  const { data: improvements, isLoading, isError } = useImprovements();
  const [filter, setFilter] = useState<Filter>("open");

  if (isLoading) return <p>Loading improvements...</p>;
  if (isError) return <p>Failed to load improvements.</p>;

  const shown = (improvements ?? []).filter((improvement) => matches(improvement, filter));

  return (
    <>
      <div>
        <label htmlFor="improvement-filter">Show</label>
        <select
          id="improvement-filter"
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
        <p>No improvements here.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Improvement</th>
              <th>Came from</th>
              <th>Status</th>
              <th>Target</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((improvement) => (
              <tr
                key={improvement.id}
                className={improvement.standing.overdue ? "row-flagged" : undefined}
              >
                <td>
                  <Link to={`/improvements/${improvement.id}`}>{improvement.title}</Link>
                  <ImprovementFlags improvement={improvement} />
                </td>
                <td>{sourceLabel(improvement.source)}</td>
                <td>
                  <StatusBadge status={improvement.standing.state} />
                </td>
                <td data-type="date">{improvement.target_date}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
