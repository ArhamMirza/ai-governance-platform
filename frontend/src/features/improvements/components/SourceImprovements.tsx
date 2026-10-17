import { Link, useNavigate } from "react-router-dom";

import { StatusBadge } from "../../../shared/components/StatusBadge";
import { useImprovementsForSource } from "../hooks";
import type { ImprovementSourceRecord } from "./ImprovementForm";

/** The improvements raised from one record -- an audit observation, a
 * concern, an incident -- and a way to raise another. Raising opens the
 * Improvements page with the form pre-filled from the record (see
 * ImprovementsPage). */
export function SourceImprovements({ from }: { from: ImprovementSourceRecord }) {
  const { data: improvements } = useImprovementsForSource(from.sourceType, from.sourceId);
  const navigate = useNavigate();

  return (
    <div>
      {improvements && improvements.length > 0 && (
        <ul>
          {improvements.map((improvement) => (
            <li key={improvement.id}>
              <Link to={`/improvements/${improvement.id}`}>{improvement.title}</Link>{" "}
              <StatusBadge status={improvement.standing.state} />
            </li>
          ))}
        </ul>
      )}
      <button onClick={() => navigate("/improvements", { state: from })}>
        Raise Improvement
      </button>
    </div>
  );
}
