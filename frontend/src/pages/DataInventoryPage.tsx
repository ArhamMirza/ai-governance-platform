import { useQuery } from "@tanstack/react-query";

import { AuditLogViewer } from "../features/audit-log/components/AuditLogViewer";
import { dataInventoryAdapter } from "../features/data-inventory/api";
import { DataInventoryGrid } from "../features/data-inventory/components/DataInventoryGrid";

export function DataInventoryPage() {
  const { data: sheet } = useQuery({
    queryKey: ["data-inventory"],
    queryFn: dataInventoryAdapter.get,
  });

  return (
    <section>
      <div className="page-header">
        <div>
          <h1>Data Inventory</h1>
          <p>Datasets used by AI systems, covering ISO 42001 A.7 (Data for AI systems) -- each entry links back to the AI system it belongs to.</p>
        </div>
      </div>

      <DataInventoryGrid />

      {/* Two trails, because they're recorded against different things: the
          sheet itself for row and column changes, and each dataset row for
          its submit/approve/withdraw history. */}
      <h3>Review History</h3>
      <AuditLogViewer entityType="DataInventoryApproval" />

      {sheet && (
        <>
          <h3>Audit Log</h3>
          <AuditLogViewer entityType="DataInventory" entityId={sheet.id} />
        </>
      )}
    </section>
  );
}
