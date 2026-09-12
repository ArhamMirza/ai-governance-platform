import { useState } from "react";

import { readError } from "../../../shared/api/readError";
import { useUpdateImpactFactor } from "../hooks";
import type { ImpactFactorAssessment } from "../types";

interface ImpactFactorCardProps {
  riskAssessmentId: number | null;
  impactAssessmentId: number;
  factorAssessment: ImpactFactorAssessment;
}

const SCORES = [1, 2, 3, 4, 5];

/** 1 is the mildest impact, 5 the most severe -- shading the chosen score
 * makes a filled-in scorecard scannable without reading every cell. */
function severityClass(score: number): string {
  if (score >= 4) return "score-high";
  if (score === 3) return "score-medium";
  return "score-low";
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

  const { factor, score } = factorAssessment;

  const save = async (
    overrides: Partial<{ benefits: string; harms: string; criteria: string; score: number | null }>,
  ) => {
    setError(null);
    try {
      await updateFactor.mutateAsync({
        factor,
        data: {
          benefits: overrides.benefits ?? benefits,
          harms: overrides.harms ?? harms,
          criteria: overrides.criteria ?? criteria,
          score: "score" in overrides ? overrides.score! : score,
        },
      });
    } catch (err) {
      setError(readError(err, "Failed to save impact factor"));
    }
  };

  return (
    <section className="impact-factor" aria-label={factor}>
      <header className="impact-factor-header">
        <h5>{factor}</h5>
        {score !== null ? (
          <span className={`impact-score-badge ${severityClass(score)}`}>{score}</span>
        ) : (
          <span className="impact-score-badge is-empty">Not scored</span>
        )}
      </header>

      {error && <p role="alert">{error}</p>}

      <div className="impact-factor-body">
        <div className="impact-factor-pair">
          <div className="impact-factor-field">
            <label htmlFor={`benefits-${factorAssessment.id}`}>Benefits</label>
            <textarea
              id={`benefits-${factorAssessment.id}`}
              aria-label={`Benefits for ${factor}`}
              rows={3}
              placeholder={`How does this system help with ${factor.toLowerCase()}?`}
              value={benefits}
              onChange={(e) => setBenefits(e.target.value)}
              onBlur={() => benefits !== (factorAssessment.benefits ?? "") && save({ benefits })}
            />
          </div>

          <div className="impact-factor-field">
            <label htmlFor={`harms-${factorAssessment.id}`}>Harms</label>
            <textarea
              id={`harms-${factorAssessment.id}`}
              aria-label={`Harms for ${factor}`}
              rows={3}
              placeholder={`What could go wrong regarding ${factor.toLowerCase()}?`}
              value={harms}
              onChange={(e) => setHarms(e.target.value)}
              onBlur={() => harms !== (factorAssessment.harms ?? "") && save({ harms })}
            />
          </div>
        </div>

        <div className="impact-factor-field">
          <label htmlFor={`criteria-${factorAssessment.id}`}>Scoring criteria</label>
          <textarea
            id={`criteria-${factorAssessment.id}`}
            aria-label={`Scoring criteria for ${factor}`}
            rows={2}
            placeholder="What would justify each score for this factor?"
            value={criteria}
            onChange={(e) => setCriteria(e.target.value)}
            onBlur={() => criteria !== (factorAssessment.criteria ?? "") && save({ criteria })}
          />
        </div>

        <div className="impact-factor-field">
          <span className="impact-factor-score-label" id={`score-label-${factorAssessment.id}`}>
            Score
          </span>
          <div
            className="impact-score-picker"
            role="radiogroup"
            aria-labelledby={`score-label-${factorAssessment.id}`}
          >
            {SCORES.map((value) => (
              <button
                key={value}
                type="button"
                role="radio"
                aria-checked={score === value}
                aria-label={`${factor} score ${value}`}
                className={`impact-score-option${score === value ? ` is-selected ${severityClass(value)}` : ""}`}
                onClick={() => save({ score: score === value ? null : value })}
              >
                {value}
              </button>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
