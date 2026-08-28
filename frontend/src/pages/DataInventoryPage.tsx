import { DataInventoryGrid } from "../features/data-inventory/components/DataInventoryGrid";

export function DataInventoryPage() {
  return (
    <section>
      <div className="page-header">
        <div>
          <h1>Data Inventory</h1>
          <p>Datasets used by AI systems, covering ISO 42001 A.7 (Data for AI systems) -- each entry links back to the AI system it belongs to.</p>
        </div>
      </div>

      <DataInventoryGrid />
    </section>
  );
}
