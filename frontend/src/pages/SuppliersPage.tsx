import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useCurrentUser } from "../features/auth/hooks";
import { hasPermission } from "../features/auth/permissions";
import { SupplierForm } from "../features/suppliers/components/SupplierForm";
import { SupplierList } from "../features/suppliers/components/SupplierList";

export function SuppliersPage() {
  const [showForm, setShowForm] = useState(false);
  const navigate = useNavigate();
  const { data: me } = useCurrentUser();
  const canEdit = hasPermission(me?.role, "edit");

  return (
    <section>
      <div className="page-header">
        <div>
          <h1>Suppliers</h1>
          <p>The third parties behind your AI systems, and what each is responsible for.</p>
        </div>
        {canEdit && (
          <button onClick={() => setShowForm((prev) => !prev)}>
            {showForm ? "Cancel" : "Add Supplier"}
          </button>
        )}
      </div>
      {showForm && <SupplierForm onCreated={(id) => navigate(`/suppliers/${id}`)} />}

      <SupplierList />
    </section>
  );
}
