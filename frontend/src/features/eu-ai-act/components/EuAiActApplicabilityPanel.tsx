import { useState } from "react";

import { ApiError } from "../../../shared/api/httpClient";
import { useEuAiActApplicability, useUpdateEuAiActApplicability } from "../hooks";
import type { EuAiActApplicability, EuAiActApplicabilityInput } from "../types";

type ScopeChoice = "yes" | "no" | "unassessed";

const ROLES: { key: keyof EuAiActApplicabilityInput; label: string; hint: string }[] = [
  { key: "is_provider", label: "Provider", hint: "You develop AI systems and put them on the market or into service under your name." },
  { key: "is_deployer", label: "Deployer", hint: "You use AI systems in your own operations." },
  { key: "is_importer", label: "Importer", hint: "You bring a non-EU provider's AI system into the EU market." },
  { key: "is_distributor", label: "Distributor", hint: "You make others' AI systems available further down the chain." },
];

function scopeChoiceOf(inScope: boolean | null): ScopeChoice {
  if (inScope === null) return "unassessed";
  return inScope ? "yes" : "no";
}

function ApplicabilityForm({ current }: { current: EuAiActApplicability }) {
  const update = useUpdateEuAiActApplicability();
  const [scope, setScope] = useState<ScopeChoice>(scopeChoiceOf(current.in_scope));
  const [justification, setJustification] = useState(current.scope_justification ?? "");
  const [roles, setRoles] = useState({
    is_provider: current.is_provider,
    is_deployer: current.is_deployer,
    is_importer: current.is_importer,
    is_distributor: current.is_distributor,
  });
  const [highRisk, setHighRisk] = useState<boolean | null>(current.has_high_risk_systems);

  const save = () =>
    update.mutate({
      in_scope: scope === "unassessed" ? null : scope === "yes",
      scope_justification: scope === "no" ? justification : null,
      ...(scope === "yes"
        ? roles
        : { is_provider: false, is_deployer: false, is_importer: false, is_distributor: false }),
      has_high_risk_systems: scope === "yes" ? highRisk : null,
    });

  return (
    <div className="criteria-editor">
      <fieldset>
        <legend>Does the EU AI Act apply to your organization?</legend>
        <p className="approval-note">
          It applies if you place AI systems on the EU market, use them in the EU, or their
          output is used in the EU (Art. 2). This is your organization's own assessment.
        </p>
        {(
          [
            ["yes", "Yes, we're in scope"],
            ["no", "No, we're outside its scope"],
            ["unassessed", "Not yet assessed"],
          ] as const
        ).map(([value, label]) => (
          <label key={value}>
            <input
              type="radio"
              name="eu-ai-act-scope"
              checked={scope === value}
              onChange={() => setScope(value)}
            />
            {label}
          </label>
        ))}
      </fieldset>

      {scope === "no" && (
        <div>
          <label htmlFor="eu-ai-act-justification">Why it doesn't apply</label>
          <textarea
            id="eu-ai-act-justification"
            value={justification}
            onChange={(e) => setJustification(e.target.value)}
          />
        </div>
      )}

      {scope === "yes" && (
        <>
          <fieldset>
            <legend>Which roles does your organization hold?</legend>
            {ROLES.map((role) => (
              <label key={role.key} title={role.hint}>
                <input
                  type="checkbox"
                  checked={roles[role.key as keyof typeof roles]}
                  onChange={(e) => setRoles({ ...roles, [role.key]: e.target.checked })}
                />
                {role.label} <span className="approval-note">{role.hint}</span>
              </label>
            ))}
          </fieldset>
          <fieldset>
            <legend>Do you provide or deploy any high-risk AI systems?</legend>
            <p className="approval-note">
              {current.high_risk_system_count === 1
                ? "1 system in your inventory is tagged high risk."
                : `${current.high_risk_system_count} systems in your inventory are tagged high risk.`}
            </p>
            <label>
              <input
                type="radio"
                name="eu-ai-act-high-risk"
                checked={highRisk === true}
                onChange={() => setHighRisk(true)}
              />
              Yes
            </label>
            <label>
              <input
                type="radio"
                name="eu-ai-act-high-risk"
                checked={highRisk === false}
                onChange={() => setHighRisk(false)}
              />
              No
            </label>
          </fieldset>
        </>
      )}

      <button onClick={save} disabled={update.isPending}>
        {update.isPending ? "Saving..." : "Save Assessment"}
      </button>
      {update.isError && (
        <p role="alert">
          {update.error instanceof ApiError ? update.error.message : "Failed to save."}
        </p>
      )}
    </div>
  );
}

export function EuAiActApplicabilityPanel() {
  const { data, isLoading, isError } = useEuAiActApplicability();

  if (isLoading) return <p>Loading EU AI Act applicability...</p>;
  if (isError || !data) return <p>Failed to load EU AI Act applicability.</p>;

  // Keyed on updated_at so a successful save re-seeds the form from what
  // the server actually stored.
  return <ApplicabilityForm key={data.updated_at ?? "unsaved"} current={data} />;
}
