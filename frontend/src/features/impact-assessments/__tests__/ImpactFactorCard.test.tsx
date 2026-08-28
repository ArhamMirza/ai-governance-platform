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

function renderCard(overrides: Partial<ImpactFactorAssessment> = {}) {
  return render(
    <ImpactFactorCard
      riskAssessmentId={1}
      impactAssessmentId={2}
      factorAssessment={{ ...factorAssessment, ...overrides }}
    />,
  );
}

describe("ImpactFactorCard", () => {
  it("shows the factor name and an unscored badge", () => {
    mockHook();

    renderCard();

    expect(screen.getByText("Fairness")).toBeInTheDocument();
    expect(screen.getByText("Not scored")).toBeInTheDocument();
  });

  it("saves benefits on blur", async () => {
    const mutateAsync = mockHook();
    const user = userEvent.setup();

    renderCard();

    await user.type(screen.getByLabelText("Benefits for Fairness"), "Standardizes screening.");
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

  it("saves the score immediately when a score button is clicked", async () => {
    const mutateAsync = mockHook();
    const user = userEvent.setup();

    renderCard();

    await user.click(screen.getByRole("radio", { name: "Fairness score 4" }));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({
        factor: "Fairness",
        data: { benefits: "", harms: "", criteria: "", score: 4 },
      });
    });
  });

  it("marks the selected score and shows it in the badge", () => {
    mockHook();

    renderCard({ score: 4 });

    expect(screen.getByRole("radio", { name: "Fairness score 4" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    expect(screen.getByText("4", { selector: ".impact-score-badge" })).toBeInTheDocument();
    expect(screen.queryByText("Not scored")).not.toBeInTheDocument();
  });

  it("clears the score when the selected one is clicked again", async () => {
    const mutateAsync = mockHook();
    const user = userEvent.setup();

    renderCard({ score: 4 });

    await user.click(screen.getByRole("radio", { name: "Fairness score 4" }));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({
        factor: "Fairness",
        data: { benefits: "", harms: "", criteria: "", score: null },
      });
    });
  });
});
