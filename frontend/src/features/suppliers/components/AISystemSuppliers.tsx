import { Link } from "react-router-dom";

import { useSuppliersForAISystem } from "../hooks";
import { supplierTypeLabel } from "../labels";
import { SupplierFlags } from "./SupplierFlags";

/** The suppliers behind one AI system, for its detail page. Links are made
 * from the supplier's side. */
export function AISystemSuppliers({ rowId }: { rowId: number }) {
  const { data: suppliers, isLoading } = useSuppliersForAISystem(rowId);

  if (isLoading) return <p>Loading suppliers...</p>;
  if (!suppliers || suppliers.length === 0) {
    return (
      <p className="framework-tags-empty">
        No suppliers linked. Link one from its page under Suppliers.
      </p>
    );
  }

  return (
    <ul className="assessment-links">
      {suppliers.map((supplier) => (
        <li key={supplier.id}>
          <Link to={`/suppliers/${supplier.id}`}>{supplier.name}</Link> —{" "}
          {supplierTypeLabel(supplier.supplier_type)}
          <SupplierFlags supplier={supplier} />
        </li>
      ))}
    </ul>
  );
}
