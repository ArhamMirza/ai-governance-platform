import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LifecycleStageTracker } from "../components/LifecycleStageTracker";
import { STAGES } from "../stages";

describe("LifecycleStageTracker", () => {
  it("shows all seven stages in ISO 5338 order", () => {
    render(<LifecycleStageTracker currentStage="inception" />);

    expect(STAGES.map((s) => s.label)).toEqual([
      "Inception",
      "Design",
      "Development",
      "Verification & Validation",
      "Deployment",
      "Operation & Monitoring",
      "Retirement",
    ]);
    expect(screen.getByText("Verification & Validation")).toBeInTheDocument();
  });

  it("marks the current stage, and the ones before it as done", () => {
    render(<LifecycleStageTracker currentStage="development" />);

    const steps = screen.getAllByRole("listitem");
    expect(steps[0].className).toContain("is-done");
    expect(steps[1].className).toContain("is-done");
    expect(steps[2].className).toContain("is-current");
    expect(steps[2]).toHaveAttribute("aria-current", "step");
    expect(steps[3].className).toContain("is-upcoming");
  });
});
