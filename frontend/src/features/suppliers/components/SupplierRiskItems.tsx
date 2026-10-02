import { Link } from "react-router-dom";

import { StatusBadge } from "../../../shared/components/StatusBadge";
import { useAISystemInventoryRows } from "../../ai-system-inventory/hooks";
import { useSupplierRiskItems } from "../hooks";
import { aiSystemName } from "../labels";

/** Risk items whose Supplier column names this supplier -- set from the
 * risk assessment's risk item grid. */
export function SupplierRiskItems({ supplierId }: { supplierId: number }) {
  const { data: items, isLoading } = useSupplierRiskItems(supplierId);
  const { data: inventory } = useAISystemInventoryRows();

  return (
    <section>
      <h3>Risks</h3>
      {isLoading ? (
        <p>Loading risks...</p>
      ) : !items || items.length === 0 ? (
        <p>No risk items name this supplier. Set a risk item's Supplier column to link one.</p>
      ) : (
        <ul className="assessment-links">
          {items.map((item) => (
            <li key={item.row_id}>
              <Link to={`/risk-assessments/${item.risk_assessment_id}`}>
                {item.category ?? "Risk item"}
              </Link>{" "}
              —{" "}
              {aiSystemName(
                inventory?.rows.find((row) => row.id === item.ai_system_row_id),
                item.ai_system_row_id,
              )}
              {item.description && <span>: {item.description}</span>}
              {item.status && <StatusBadge status={item.status} />}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
