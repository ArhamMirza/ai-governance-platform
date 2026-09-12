import { useState } from "react";

import { readError } from "../../../shared/api/readError";
import { useOrgChart, useUpdateGovernanceRole } from "../hooks";
import type { OrgChartNode } from "../types";

const BOX_WIDTH = 180;
const BOX_HEIGHT = 84;
const H_GAP = 24;
const V_GAP = 56;

interface PositionedNode extends OrgChartNode {
  x: number;
  y: number;
  depth: number;
}

/** Depth-first layout purely from parent_role_id -- no saved positions, no
 * drag-and-drop. Children are placed left-to-right under their parent;
 * width per subtree keeps siblings from overlapping. A node whose parent
 * was deleted or forms a cycle degrades to a second root rather than being
 * dropped, so nothing silently vanishes from the chart. */
function layout(nodes: OrgChartNode[]): { positioned: PositionedNode[]; width: number; height: number } {
  const byParent = new Map<number | null, OrgChartNode[]>();
  const ids = new Set(nodes.map((n) => n.id));
  for (const node of nodes) {
    const parentKey = node.parent_role_id !== null && ids.has(node.parent_role_id)
      ? node.parent_role_id
      : null;
    if (!byParent.has(parentKey)) byParent.set(parentKey, []);
    byParent.get(parentKey)!.push(node);
  }

  const positioned: PositionedNode[] = [];
  const seen = new Set<number>();
  let cursorX = 0;
  let maxDepth = 0;

  function place(node: OrgChartNode, depth: number): number {
    if (seen.has(node.id)) return cursorX; // Cycle guard -- see module doc.
    seen.add(node.id);
    maxDepth = Math.max(maxDepth, depth);
    const children = byParent.get(node.id) ?? [];

    if (children.length === 0) {
      const x = cursorX;
      cursorX += BOX_WIDTH + H_GAP;
      positioned.push({ ...node, x, y: depth * (BOX_HEIGHT + V_GAP), depth });
      return x;
    }

    const childXs = children.map((child) => place(child, depth + 1));
    const x = (childXs[0] + childXs[childXs.length - 1]) / 2;
    positioned.push({ ...node, x, y: depth * (BOX_HEIGHT + V_GAP), depth });
    return x;
  }

  for (const root of byParent.get(null) ?? []) {
    place(root, 0);
  }

  const width = Math.max(cursorX - H_GAP, BOX_WIDTH);
  const height = (maxDepth + 1) * (BOX_HEIGHT + V_GAP) - V_GAP;
  return { positioned, width, height };
}

interface OrgChartProps {
  canManage: boolean;
}

export function OrgChart({ canManage }: OrgChartProps) {
  const { data: nodes, isLoading, isError } = useOrgChart();
  const update = useUpdateGovernanceRole();
  const [error, setError] = useState<string | null>(null);

  if (isLoading) return <p>Loading the org chart...</p>;
  if (isError || !nodes) return <p>Failed to load the org chart.</p>;
  if (nodes.length === 0) return <p>No governance roles defined yet.</p>;

  const { positioned, width, height } = layout(nodes);
  const byId = new Map(positioned.map((n) => [n.id, n]));

  const handleReparent = async (nodeId: number, parentRoleId: string) => {
    setError(null);
    try {
      await update.mutateAsync({
        roleId: nodeId,
        data: { parent_role_id: parentRoleId ? Number(parentRoleId) : null },
      });
    } catch (err) {
      setError(readError(err, "Failed to change who this role reports to"));
    }
  };

  return (
    <div className="org-chart-wrapper">
      {error && <p role="alert">{error}</p>}
      <svg
        viewBox={`0 0 ${width + BOX_WIDTH} ${height + BOX_HEIGHT}`}
        width={width + BOX_WIDTH}
        height={height + BOX_HEIGHT}
        role="img"
        aria-label="Governance role org chart"
      >
        {positioned.map((node) => {
          if (node.parent_role_id === null) return null;
          const parent = byId.get(node.parent_role_id);
          if (!parent) return null;
          const x1 = parent.x + BOX_WIDTH / 2;
          const y1 = parent.y + BOX_HEIGHT;
          const x2 = node.x + BOX_WIDTH / 2;
          const y2 = node.y;
          return (
            <path
              key={`edge-${node.id}`}
              d={`M ${x1} ${y1} V ${y1 + V_GAP / 2} H ${x2} V ${y2}`}
              className="org-chart-edge"
            />
          );
        })}

        {positioned.map((node) => (
          <foreignObject
            key={node.id}
            x={node.x}
            y={node.y}
            width={BOX_WIDTH}
            height={BOX_HEIGHT}
          >
            <div className="org-chart-box">
              <strong>{node.name}</strong>
              <span className="gate-detail">
                {node.holders.length === 0
                  ? "Vacant"
                  : node.holders.map((h) => h.name).join(", ")}
              </span>
              {canManage && (
                <select
                  aria-label={`${node.name} reports to`}
                  value={node.parent_role_id ?? ""}
                  onChange={(e) => handleReparent(node.id, e.target.value)}
                >
                  <option value="">Nobody (top of the chart)</option>
                  {nodes
                    .filter((n) => n.id !== node.id)
                    .map((option) => (
                      <option key={option.id} value={option.id}>
                        {option.name}
                      </option>
                    ))}
                </select>
              )}
            </div>
          </foreignObject>
        ))}
      </svg>
    </div>
  );
}
