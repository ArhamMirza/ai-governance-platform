import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ImpactFactorCard } from "../components/ImpactFactorCard";
import { useUpdateImpactFactor } from "../hooks";
import type { ImpactFactorAssessment } from "../types";

vi.mock("../hooks");

const factorAssessment: ImpactFactorAssessment = {
  id: 1,
  factor: "Fairness",
  benefits: null,
  harms: null,
  criteria: null,
  score: null,
};

function mockHook(mutateAsync = vi.fn()) {
  vi.mocked(useUpdateImpactFactor).mockReturnValue({ mutateAsync, isPending: false } as never);
  return mutateAsync;
}

describe("ImpactFactorCard", () => {
  it("shows the factor name and blank fields", () => {
    mockHook();

    render(
      <ImpactFactorCard
        riskAssessmentId={1}
        impactAssessmentId={2}
        factorAssessment={factorAssessment}
      />,
    );

    expect(screen.getByText("Fairness")).toBeInTheDocument();
    expect(screen.getByLabelText("Score (1-5)")).toHaveValue("");
  });

  it("saves benefits on blur", async () => {
    const mutateAsync = mockHook();
    const user = userEvent.setup();

    render(
      <ImpactFactorCard
        riskAssessmentId={1}
        impactAssessmentId={2}
        factorAssessment={factorAssessment}
      />,
    );

    await user.type(screen.getByLabelText("Benefits"), "Standardizes screening.");
    await user.tab();

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({
        factor: "Fairness",
        data: {
          benefits: "Standardizes screening.",
          harms: "",
          criteria: "",
          score: null,
        },
      });
    });
  });

  it("saves the score immediately on change", async () => {
    const mutateAsync = mockHook();
    const user = userEvent.setup();

    render(
      <ImpactFactorCard
        riskAssessmentId={1}
        impactAssessmentId={2}
        factorAssessment={factorAssessment}
      />,
    );

    await user.selectOptions(screen.getByLabelText("Score (1-5)"), "4");

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({
        factor: "Fairness",
        data: { benefits: "", harms: "", criteria: "", score: 4 },
      });
    });
  });
});
