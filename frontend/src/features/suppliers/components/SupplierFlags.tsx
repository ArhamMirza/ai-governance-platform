import type { Supplier } from "../types";

/** The chips a supplier carries wherever it's listed. */
export function SupplierFlags({ supplier }: { supplier: Supplier }) {
  return (
    <>
      {supplier.contract_status === "expired" && (
        <span className="flag-chip">Contract ended</span>
      )}
      {supplier.contract_status === "expiring" && (
        <span className="flag-chip">Contract ending soon</span>
      )}
      {supplier.review_overdue && <span className="flag-chip">Review overdue</span>}
    </>
  );
}
