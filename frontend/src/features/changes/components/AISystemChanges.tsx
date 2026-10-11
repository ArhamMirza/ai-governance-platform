import { Link } from "react-router-dom";

import { StatusBadge } from "../../../shared/components/StatusBadge";
import { useChangesForAISystem } from "../hooks";
import { ChangeFlags } from "./ChangeList";

/** The planned changes that affect one AI system, on its page. Links are
 * made from the change's side. */
export function AISystemChanges({ rowId }: { rowId: number }) {
  const { data: changes, isLoading } = useChangesForAISystem(rowId);

  if (isLoading) return <p>Loading changes...</p>;
  if (!changes || changes.length === 0) {
    return (
      <p className="framework-tags-empty">
        No planned changes affect this system. Link one from its page under Changes.
      </p>
    );
  }

  return (
    <ul className="assessment-links">
      {changes.map((change) => (
        <li key={change.id}>
          <Link to={`/changes/${change.id}`}>{change.title}</Link>{" "}
          <StatusBadge status={change.standing.state} />
          <ChangeFlags change={change} />
        </li>
      ))}
    </ul>
  );
}
