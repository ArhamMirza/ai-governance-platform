import { Link } from "react-router-dom";

import { useSuppliersForAISystem } from "../hooks";
import { ART25_WARNING, supplierRoleLabel } from "../labels";
import { SupplierFlags } from "./SupplierFlags";

/** The suppliers behind one AI system, with each one's role for *this*
 * system -- on the AI system page and on its impact and risk assessments.
 * Derived through the AI system's own supplier links, so the three pages
 * can never disagree. Links are made from the supplier's side. */
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
      {suppliers.map((supplier) => {
        const link = supplier.ai_system_links.find((l) => l.ai_system_row_id === rowId);
        return (
          <li key={supplier.id}>
            <Link to={`/suppliers/${supplier.id}`}>{supplier.name}</Link> —{" "}
            {supplierRoleLabel(link?.supplier_role ?? null)}
            <SupplierFlags supplier={supplier} />
            {link?.art25_triggered && <p className="inline-warning">{ART25_WARNING}</p>}
          </li>
        );
      })}
    </ul>
  );
}
