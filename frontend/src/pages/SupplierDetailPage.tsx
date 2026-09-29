import { useParams } from "react-router-dom";

import { SupplierDetail } from "../features/suppliers/components/SupplierDetail";

export function SupplierDetailPage() {
  const { supplierId } = useParams<{ supplierId: string }>();
  const id = Number(supplierId);

  if (!supplierId || Number.isNaN(id)) return <p>Invalid supplier id.</p>;

  return <SupplierDetail supplierId={id} />;
}
