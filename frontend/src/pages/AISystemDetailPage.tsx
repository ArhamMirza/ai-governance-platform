import { useParams } from "react-router-dom";

import { AISystemDetail } from "../features/ai-systems/components/AISystemDetail";

export function AISystemDetailPage() {
  const { rowId } = useParams<{ rowId: string }>();
  const id = Number(rowId);
  if (!rowId || Number.isNaN(id)) return <p>Invalid AI system id.</p>;
  return <AISystemDetail rowId={id} />;
}
