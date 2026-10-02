import { useState } from "react";

import { useAISystemInventoryRows } from "../../ai-system-inventory/hooks";
import { useSetSupplierAISystems, useUpdateSupplierAISystemLink } from "../hooks";
import { ART25_TRIGGERS, ART25_WARNING, SUPPLIER_ROLE_OPTIONS, aiSystemName } from "../labels";
import type { SupplierAISystemLink, SupplierDetail, SupplierRole } from "../types";

/** Which AI systems the supplier contributes to, what it is for each one,
 * and anything your organization did with it that triggers Art. 25(1). */
export function SupplierAISystemLinks({ supplier }: { supplier: SupplierDetail }) {
  const { data: inventory } = useAISystemInventoryRows();
  const setLinks = useSetSupplierAISystems(supplier.id);
  const updateLink = useUpdateSupplierAISystemLink(supplier.id);
  const [adding, setAdding] = useState("");

  const rows = inventory?.rows ?? [];
  const nameOf = (rowId: number) => aiSystemName(rows.find((row) => row.id === rowId), rowId);
  const unlinked = rows.filter((row) => !supplier.ai_system_row_ids.includes(row.id));

  const save = (link: SupplierAISystemLink, change: Partial<SupplierAISystemLink>) => {
    const next = { ...link, ...change };
    updateLink.mutate({
      aiSystemRowId: link.ai_system_row_id,
      data: {
        supplier_role: next.supplier_role,
        rebranded: next.rebranded,
        substantially_modified: next.substantially_modified,
        repurposed_to_high_risk: next.repurposed_to_high_risk,
      },
    });
  };

  return (
    <section>
      <h3>AI Systems</h3>
      <p>Which AI systems this supplier contributes to, and its EU AI Act role for each.</p>
      {supplier.ai_system_links.length === 0 ? (
        <p>Not linked to any AI system yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>AI system</th>
              <th>Supplier's role</th>
              <th>What your organization did (Art. 25)</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {supplier.ai_system_links.map((link) => {
              const name = nameOf(link.ai_system_row_id);
              return (
                <tr key={link.ai_system_row_id} className={link.art25_triggered ? "row-flagged" : undefined}>
                  <td>{name}</td>
                  <td>
                    <select
                      aria-label={`Supplier's role for ${name}`}
                      value={link.supplier_role ?? ""}
                      onChange={(e) =>
                        save(link, {
                          supplier_role: (e.target.value || null) as SupplierRole | null,
                        })
                      }
                      disabled={updateLink.isPending}
                    >
                      <option value="">Not recorded</option>
                      {SUPPLIER_ROLE_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    {ART25_TRIGGERS.map((trigger) => (
                      <label key={trigger.key}>
                        <input
                          type="checkbox"
                          checked={link[trigger.key]}
                          onChange={(e) => save(link, { [trigger.key]: e.target.checked })}
                          disabled={updateLink.isPending}
                        />
                        {trigger.label}
                      </label>
                    ))}
                    {link.art25_triggered && <p className="flag-chip">{ART25_WARNING}</p>}
                  </td>
                  <td>
                    <button
                      onClick={() =>
                        setLinks.mutate(
                          supplier.ai_system_row_ids.filter((id) => id !== link.ai_system_row_id),
                        )
                      }
                      disabled={setLinks.isPending}
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}

      {unlinked.length > 0 && (
        <div className="inline-form">
          <label htmlFor="supplier-add-ai-system">Add AI system</label>
          <select
            id="supplier-add-ai-system"
            value={adding}
            onChange={(e) => setAdding(e.target.value)}
          >
            <option value="">Choose an AI system</option>
            {unlinked.map((row) => (
              <option key={row.id} value={row.id}>
                {aiSystemName(row, row.id)}
              </option>
            ))}
          </select>
          <button
            onClick={() => {
              setLinks.mutate([...supplier.ai_system_row_ids, Number(adding)]);
              setAdding("");
            }}
            disabled={!adding || setLinks.isPending}
          >
            Link
          </button>
        </div>
      )}
    </section>
  );
}
