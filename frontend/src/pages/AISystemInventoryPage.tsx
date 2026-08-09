import { AISystemInventoryGrid } from "../features/ai-system-inventory/components/AISystemInventoryGrid";

export function AISystemInventoryPage() {
  return (
    <section>
      <h1>AI System Inventory</h1>
      <p>Registered AI systems are managed here.</p>
      <AISystemInventoryGrid />
    </section>
  );
}
