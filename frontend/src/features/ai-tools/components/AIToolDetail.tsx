import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { readError } from "../../../shared/api/readError";
import { AuditLogViewer } from "../../audit-log/components/AuditLogViewer";
import { FrameworkTagPicker } from "../../framework-tags/components/FrameworkTagPicker";
import { useSuppliers } from "../../suppliers/hooks";
import { formatUserOption } from "../../users/formatUserOption";
import { useUserDirectory } from "../../users/hooks";
import { useAITool, useDecideAITool, useDeleteAITool, useUpdateAITool } from "../hooks";
import {
  ACTION_LABELS,
  CLASSIFICATION_OPTIONS,
  actionsFor,
  classificationLabel,
  isWeb,
  kindLabel,
  splitDomains,
} from "../labels";
import type { AITool, AIToolAction, AIToolUpdateInput, DataClassification } from "../types";
import { AIToolFlags } from "./AIToolList";
import { AIToolStatusBadge } from "./AIToolStatusBadge";

type TextField = "name" | "vendor" | "description";

const TEXT_FIELDS: { key: TextField; label: string; multiline: boolean }[] = [
  { key: "name", label: "Tool", multiline: false },
  { key: "vendor", label: "Vendor", multiline: false },
  { key: "description", label: "What it is", multiline: true },
];

/** The Chief AI Governance Officer's decision on the tool. The server
 * refuses anyone else, so the buttons are shown to everyone who can open the
 * page and the refusal is explained rather than hidden. */
function DecisionPanel({ tool }: { tool: AITool }) {
  const decide = useDecideAITool(tool.id);
  const [classification, setClassification] = useState<DataClassification>(
    tool.max_data_classification,
  );
  const [conditions, setConditions] = useState(tool.conditions_of_use ?? "");
  const [reviewDue, setReviewDue] = useState("");
  const [note, setNote] = useState("");

  const actions = actionsFor(tool.status);
  const revoking = (action: AIToolAction) => action === "revoke";

  const move = async (action: AIToolAction) => {
    await decide.mutateAsync({
      action,
      max_data_classification: revoking(action) ? null : classification,
      conditions_of_use: revoking(action) ? null : conditions.trim() || null,
      review_due: revoking(action) ? null : reviewDue || null,
      note: note.trim() || null,
    });
    setNote("");
    setReviewDue("");
  };

  return (
    <section>
      <h3>Decision</h3>
      <p className="approval-note">
        Only the Chief AI Governance Officer can approve, limit or withdraw a tool.
      </p>
      {tool.decided_on && (
        <p>
          Last decided {tool.decided_on}
          {tool.decision_note && `: ${tool.decision_note}`}
        </p>
      )}
      <div>
        <label htmlFor="ai-tool-classification">The most sensitive data it may be given</label>
        <select
          id="ai-tool-classification"
          value={classification}
          onChange={(e) => setClassification(e.target.value as DataClassification)}
        >
          {CLASSIFICATION_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label} -- {option.hint}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="ai-tool-conditions">Conditions of use</label>
        <textarea
          id="ai-tool-conditions"
          value={conditions}
          onChange={(e) => setConditions(e.target.value)}
        />
      </div>
      <div>
        <label htmlFor="ai-tool-review-due">Review by (a year on if left empty)</label>
        <input
          id="ai-tool-review-due"
          type="date"
          value={reviewDue}
          onChange={(e) => setReviewDue(e.target.value)}
        />
      </div>
      <div>
        <label htmlFor="ai-tool-note">Note (needed to withdraw access)</label>
        <input id="ai-tool-note" value={note} onChange={(e) => setNote(e.target.value)} />
      </div>
      <div className="detail-actions">
        {actions.map((action) => (
          <button
            key={action}
            onClick={() => move(action)}
            disabled={decide.isPending || (revoking(action) && !note.trim())}
          >
            {ACTION_LABELS[action]}
          </button>
        ))}
      </div>
      {decide.isError && (
        <p role="alert">{readError(decide.error, "Failed to record the decision.")}</p>
      )}
    </section>
  );
}

export function AIToolDetail({ toolId }: { toolId: number }) {
  const { data: tool, isLoading, isError } = useAITool(toolId);
  const { data: directory } = useUserDirectory();
  const { data: suppliers } = useSuppliers();
  const update = useUpdateAITool(toolId);
  const deleteTool = useDeleteAITool();
  const navigate = useNavigate();

  if (isLoading) return <p>Loading AI tool...</p>;
  if (isError || !tool) return <p>Failed to load AI tool.</p>;

  const save = (data: AIToolUpdateInput) => update.mutate(data);
  const allowed = tool.status === "approved" || tool.status === "restricted";
  const deletable = tool.status === "catalogued" && tool.decided_on === null;

  const handleDelete = async () => {
    if (!window.confirm(`Delete "${tool.name}"?`)) return;
    await deleteTool.mutateAsync(toolId);
    navigate("/ai-tools");
  };

  const textInput = ({ key, label, multiline }: (typeof TEXT_FIELDS)[number]) => {
    const props = {
      id: `ai-tool-${key}`,
      defaultValue: tool[key] ?? "",
      onBlur: (e: React.FocusEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        if (e.target.value !== (tool[key] ?? "")) {
          // A name can't be blank; the others clear to null.
          if (key === "name" && !e.target.value.trim()) return;
          save({ [key]: e.target.value.trim() || null });
        }
      },
    };
    return (
      <div key={key}>
        <label htmlFor={props.id}>{label}</label>
        {multiline ? <textarea {...props} /> : <input {...props} />}
      </div>
    );
  };

  return (
    <article key={tool.updated_at}>
      <header className="record-header">
        <div className="record-header-top">
          <h2>{tool.name}</h2>
          <AIToolStatusBadge status={tool.status} />
          <AIToolFlags tool={tool} />
        </div>
        <p>
          {kindLabel(tool.kind)}
          {tool.domains.length > 0 && ` · ${tool.domains.join(", ")}`}
          {allowed &&
            ` · may be given ${classificationLabel(tool.max_data_classification).toLowerCase()} data`}
          {tool.review_due && ` · review by ${tool.review_due}`}
        </p>
      </header>

      <DecisionPanel key={`${tool.status}-${tool.updated_at}`} tool={tool} />

      {TEXT_FIELDS.map(textInput)}
      {isWeb(tool.kind) && (
        <div>
          <label htmlFor="ai-tool-domains-edit">Addresses</label>
          <textarea
            id="ai-tool-domains-edit"
            defaultValue={tool.domains.join("\n")}
            onBlur={(e) => {
              const domains = splitDomains(e.target.value);
              if (domains.length > 0 && domains.join("\n") !== tool.domains.join("\n")) {
                save({ domains });
              }
            }}
          />
        </div>
      )}
      <div>
        <label htmlFor="ai-tool-owner">Owner</label>
        <select
          id="ai-tool-owner"
          value={tool.owner_id ?? ""}
          onChange={(e) => save({ owner_id: e.target.value ? Number(e.target.value) : null })}
        >
          <option value="">Unassigned</option>
          {(directory ?? []).map((user) => (
            <option key={user.id} value={user.id}>
              {formatUserOption(user)}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="ai-tool-supplier">Supplier record</label>
        <select
          id="ai-tool-supplier"
          value={tool.supplier_id ?? ""}
          onChange={(e) => save({ supplier_id: e.target.value ? Number(e.target.value) : null })}
        >
          <option value="">None</option>
          {(suppliers ?? []).map((supplier) => (
            <option key={supplier.id} value={supplier.id}>
              {supplier.name}
            </option>
          ))}
        </select>
      </div>
      {update.isError && (
        <p role="alert">{readError(update.error, "Failed to save the tool.")}</p>
      )}

      <h3>Framework Tags</h3>
      <FrameworkTagPicker entityType="AITool" entityId={toolId} />

      <AuditLogViewer entityType="AITool" entityId={toolId} />

      <div className="detail-actions">
        {deletable ? (
          <button onClick={handleDelete} disabled={deleteTool.isPending}>
            Delete Tool
          </button>
        ) : (
          <p className="approval-note">
            Once decided on or requested, a tool stays on record. Withdraw access instead of
            deleting it.
          </p>
        )}
        {deleteTool.isError && (
          <p role="alert">{readError(deleteTool.error, "Failed to delete the tool.")}</p>
        )}
      </div>
    </article>
  );
}
