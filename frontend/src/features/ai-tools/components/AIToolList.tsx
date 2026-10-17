import { useState } from "react";
import { Link } from "react-router-dom";

import { useAITools } from "../hooks";
import { classificationLabel, isFlagged } from "../labels";
import type { AITool, AIToolStatus } from "../types";
import { AIToolStatusBadge } from "./AIToolStatusBadge";

type Filter = "all" | "allowed" | AIToolStatus;

const FILTERS: { value: Filter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "allowed", label: "Allowed (approved or limited)" },
  { value: "catalogued", label: "Not approved" },
  { value: "revoked", label: "Access withdrawn" },
];

function matches(tool: AITool, filter: Filter): boolean {
  if (filter === "all") return true;
  if (filter === "allowed") return tool.status === "approved" || tool.status === "restricted";
  return tool.status === filter;
}

/** The chip a tool carries wherever it's listed. */
export function AIToolFlags({ tool }: { tool: AITool }) {
  return isFlagged(tool) ? <span className="flag-chip">Review overdue</span> : null;
}

export function AIToolList() {
  const { data: tools, isLoading, isError } = useAITools();
  const [filter, setFilter] = useState<Filter>("all");

  if (isLoading) return <p>Loading AI tools...</p>;
  if (isError) return <p>Failed to load AI tools.</p>;

  const shown = (tools ?? []).filter((tool) => matches(tool, filter));

  return (
    <>
      <div>
        <label htmlFor="ai-tool-filter">Show</label>
        <select
          id="ai-tool-filter"
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
        <p>No AI tools here.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Tool</th>
              <th>Address</th>
              <th>Status</th>
              <th>May be given</th>
              <th>Review due</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((tool) => {
              const allowed = tool.status === "approved" || tool.status === "restricted";
              return (
                <tr key={tool.id} className={isFlagged(tool) ? "row-flagged" : undefined}>
                  <td>
                    <Link to={`/ai-tools/${tool.id}`}>{tool.name}</Link>
                    <AIToolFlags tool={tool} />
                    {tool.vendor && <div className="approval-note">{tool.vendor}</div>}
                  </td>
                  <td>{tool.domains.join(", ")}</td>
                  <td>
                    <AIToolStatusBadge status={tool.status} />
                  </td>
                  <td>{allowed ? `${classificationLabel(tool.max_data_classification)} data` : "—"}</td>
                  <td data-type="date">{tool.review_due ?? "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </>
  );
}
