import { useState } from "react";

import { ApiError } from "../../../shared/api/httpClient";
import { useUpdateImpactFactor } from "../hooks";
import type { ImpactFactorAssessment } from "../types";

interface ImpactFactorCardProps {
  riskAssessmentId: number;
  impactAssessmentId: number;
  factorAssessment: ImpactFactorAssessment;
}

function readError(err: unknown, fallback: string): string {
  if (!(err instanceof ApiError)) return fallback;
  try {
    const parsed = JSON.parse(err.message) as { detail?: string };
    return parsed.detail ?? err.message;
  } catch {
    return err.message || fallback;
  }
}

export function ImpactFactorCard({
  riskAssessmentId,
  impactAssessmentId,
  factorAssessment,
}: ImpactFactorCardProps) {
  const updateFactor = useUpdateImpactFactor(riskAssessmentId, impactAssessmentId);
  const [benefits, setBenefits] = useState(factorAssessment.benefits ?? "");
  const [harms, setHarms] = useState(factorAssessment.harms ?? "");
  const [criteria, setCriteria] = useState(factorAssessment.criteria ?? "");
  const [error, setError] = useState<string | null>(null);

  const save = async (overrides: Partial<{ benefits: string; harms: string; criteria: string; score: number | null }>) => {
    setError(null);
    try {
      await updateFactor.mutateAsync({
        factor: factorAssessment.factor,
        data: {
          benefits: overrides.benefits ?? benefits,
          harms: overrides.harms ?? harms,
          criteria: overrides.criteria ?? criteria,
          score: "score" in overrides ? overrides.score! : factorAssessment.score,
        },
      });
    } catch (err) {
      setError(readError(err, "Failed to save impact factor"));
    }
  };

  const handleScoreChange = (value: string) => {
    const score = value === "" ? null : Number(value);
    save({ score });
  };

  return (
    <fieldset className="impact-factor-card">
      <legend>{factorAssessment.factor}</legend>
      {error && <p role="alert">{error}</p>}

      <label htmlFor={`benefits-${factorAssessment.id}`}>Benefits</label>
      <textarea
        id={`benefits-${factorAssessment.id}`}
        rows={2}
        value={benefits}
        onChange={(e) => setBenefits(e.target.value)}
        onBlur={() => benefits !== (factorAssessment.benefits ?? "") && save({ benefits })}
      />

      <label htmlFor={`harms-${factorAssessment.id}`}>Harms</label>
      <textarea
        id={`harms-${factorAssessment.id}`}
        rows={2}
        value={harms}
        onChange={(e) => setHarms(e.target.value)}
        onBlur={() => harms !== (factorAssessment.harms ?? "") && save({ harms })}
      />

      <label htmlFor={`criteria-${factorAssessment.id}`}>Scoring Criteria</label>
      <textarea
        id={`criteria-${factorAssessment.id}`}
        rows={2}
        value={criteria}
        onChange={(e) => setCriteria(e.target.value)}
        onBlur={() => criteria !== (factorAssessment.criteria ?? "") && save({ criteria })}
      />

      <label htmlFor={`score-${factorAssessment.id}`}>Score (1-5)</label>
      <select
        id={`score-${factorAssessment.id}`}
        value={factorAssessment.score ?? ""}
        onChange={(e) => handleScoreChange(e.target.value)}
      >
        <option value="">Not scored</option>
        {[1, 2, 3, 4, 5].map((n) => (
          <option key={n} value={n}>
            {n}
          </option>
        ))}
      </select>
    </fieldset>
  );
}
