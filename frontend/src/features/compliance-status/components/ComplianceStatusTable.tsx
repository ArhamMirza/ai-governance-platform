import { useState } from "react";

import { StatusBadge } from "../../../shared/components/StatusBadge";
import { useComplianceStatus } from "../hooks";
import type { TaggedItemStatus } from "../types";

// A control in either of these states is the thing this page exists to
// surface -- everything satisfied or explicitly excluded needs no attention.
const GAP_STATUSES = new Set(["no_coverage", "partial"]);

function TaggedItemChips({ items }: { items: TaggedItemStatus[] }) {
  if (items.length === 0) {
    return <span className="framework-tags-empty">Not tagged to anything yet.</span>;
  }
  return (
    <div className="framework-tag-chips">
      {items.map((item) => (
        <span
          key={`${item.entity_type}-${item.entity_id}`}
          className="framework-tag-chip"
          data-current={item.current}
          title={item.detail}
        >
          {item.entity_type}: {item.label}
        </span>
      ))}
    </div>
  );
}

interface ComplianceStatusTableProps {
  framework?: string;
}

export function ComplianceStatusTable({ framework }: ComplianceStatusTableProps) {
  const { data: controls, isLoading, isError } = useComplianceStatus(framework);
  const [gapsOnly, setGapsOnly] = useState(false);

  if (isLoading) return <p>Loading compliance status...</p>;
  if (isError || !controls) return <p>Failed to load compliance status.</p>;

  const rows = gapsOnly ? controls.filter((control) => GAP_STATUSES.has(control.status)) : controls;

  return (
    <div className="data-grid">
      <div className="page-header">
        <div />
        <label>
          <input
            type="checkbox"
            checked={gapsOnly}
            onChange={(e) => setGapsOnly(e.target.checked)}
          />{" "}
          Show gaps only
        </label>
      </div>

      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Code</th>
              <th>Title</th>
              <th>Status</th>
              <th>Reason</th>
              <th>Tagged Items</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={5}>
                  {gapsOnly ? "No gaps -- everything applicable is covered." : "Nothing to show."}
                </td>
              </tr>
            ) : (
              rows.map((control) => (
                <tr key={control.id}>
                  <td>{control.code}</td>
                  <td>{control.title}</td>
                  <td data-column="status" data-type="text">
                    <StatusBadge status={control.status} />
                  </td>
                  <td>{control.reason}</td>
                  <td>
                    <TaggedItemChips items={control.tagged_items} />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
