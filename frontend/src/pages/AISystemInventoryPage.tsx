import { useQuery } from "@tanstack/react-query";

import { AuditLogViewer } from "../features/audit-log/components/AuditLogViewer";
import { aiSystemInventoryAdapter } from "../features/ai-system-inventory/api";
import { AISystemInventoryGrid } from "../features/ai-system-inventory/components/AISystemInventoryGrid";

export function AISystemInventoryPage() {
  const { data: sheet } = useQuery({
    queryKey: ["ai-system-inventory"],
    queryFn: aiSystemInventoryAdapter.get,
  });

  return (
    <section>
      <div className="page-header">
        <div>
          <h1>AI System Inventory</h1>
          <p>Registered AI systems are managed here.</p>
        </div>
      </div>
      <AISystemInventoryGrid />

      {sheet && (
        <>
          <AuditLogViewer entityType="AISystemInventory" entityId={sheet.id} />
        </>
      )}
    </section>
  );
}
