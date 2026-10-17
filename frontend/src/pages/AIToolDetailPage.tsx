import { useParams } from "react-router-dom";

import { AIToolDetail } from "../features/ai-tools/components/AIToolDetail";

export function AIToolDetailPage() {
  const { toolId } = useParams<{ toolId: string }>();
  const id = Number(toolId);

  if (!toolId || Number.isNaN(id)) return <p>Invalid tool id.</p>;

  return <AIToolDetail toolId={id} />;
}
