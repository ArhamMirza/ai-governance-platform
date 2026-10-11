import { AISystemLinkPicker } from "../../ai-systems/components/AISystemLinkPicker";
import { useSetObjectiveAISystems } from "../hooks";
import type { ObjectiveDetail } from "../types";

/** The AI systems an objective measures or concerns -- each one's page
 * lists the objective back. */
export function ObjectiveAISystemLinks({ objective }: { objective: ObjectiveDetail }) {
  const setLinks = useSetObjectiveAISystems(objective.id);

  return (
    <section>
      <h3>AI Systems</h3>
      <AISystemLinkPicker
        idPrefix="objective"
        value={objective.ai_system_row_ids}
        pending={setLinks.isPending}
        onChange={(rowIds) => setLinks.mutate(rowIds)}
      />
    </section>
  );
}
