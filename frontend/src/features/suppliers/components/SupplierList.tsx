import { Link } from "react-router-dom";

import { StatusBadge } from "../../../shared/components/StatusBadge";
import { useSuppliers } from "../hooks";
import { supplierTypeLabel } from "../labels";
import { SupplierFlags } from "./SupplierFlags";

export function SupplierList() {
  const { data: suppliers, isLoading, isError } = useSuppliers();

  if (isLoading) return <p>Loading suppliers...</p>;
  if (isError) return <p>Failed to load suppliers.</p>;
  if (!suppliers || suppliers.length === 0) {
    return <p>No suppliers yet.</p>;
  }

  return (
    <table>
      <thead>
        <tr>
          <th>Supplier</th>
          <th>Type</th>
          <th>Status</th>
          <th>Contract ends</th>
          <th>Next review</th>
        </tr>
      </thead>
      <tbody>
        {suppliers.map((supplier) => (
          <tr
            key={supplier.id}
            className={
              supplier.review_overdue || supplier.contract_status ? "row-flagged" : undefined
            }
          >
            <td>
              <Link to={`/suppliers/${supplier.id}`}>{supplier.name}</Link>
              <SupplierFlags supplier={supplier} />
            </td>
            <td>{supplierTypeLabel(supplier.supplier_type)}</td>
            <td>
              <StatusBadge status={supplier.status} />
            </td>
            <td data-type="date">{supplier.contract_end ?? "—"}</td>
            <td data-type="date">{supplier.next_review_due ?? "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
