import { Link } from "react-router-dom";

import { StatusBadge } from "../../../shared/components/StatusBadge";
import { useObjectivesForAISystem } from "../hooks";
import { ObjectiveFlags } from "./ObjectiveList";

/** The AI objectives measuring or concerning one AI system, on its page.
 * Links are made from the objective's side. */
export function AISystemObjectives({ rowId }: { rowId: number }) {
  const { data: objectives, isLoading } = useObjectivesForAISystem(rowId);

  if (isLoading) return <p>Loading objectives...</p>;
  if (!objectives || objectives.length === 0) {
    return (
      <p className="framework-tags-empty">
        No AI objectives linked. Link one from its page under AI Objectives.
      </p>
    );
  }

  return (
    <ul className="assessment-links">
      {objectives.map((objective) => (
        <li key={objective.id}>
          <Link to={`/objectives/${objective.id}`}>{objective.title}</Link>{" "}
          <StatusBadge status={objective.standing.state} />
          <ObjectiveFlags objective={objective} />
        </li>
      ))}
    </ul>
  );
}
