import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ProgressRing } from "../ProgressRing";
import { SegmentedBar } from "../SegmentedBar";

describe("SegmentedBar", () => {
  it("renders a legend entry for every segment, including empty ones", () => {
    render(
      <SegmentedBar
        segments={[
          { key: "high", label: "High", value: 2, tone: "high" },
          { key: "low", label: "Low", value: 0, tone: "low" },
        ]}
      />,
    );

    expect(screen.getByText("High")).toBeInTheDocument();
    expect(screen.getByText("Low")).toBeInTheDocument();
  });

  it("sizes fills proportionally", () => {
    const { container } = render(
      <SegmentedBar
        segments={[
          { key: "a", label: "A", value: 3, tone: "high" },
          { key: "b", label: "B", value: 1, tone: "low" },
        ]}
      />,
    );

    const fills = container.querySelectorAll(".segmented-bar-fill");
    expect(fills).toHaveLength(2);
    expect((fills[0] as HTMLElement).style.width).toBe("75%");
    expect((fills[1] as HTMLElement).style.width).toBe("25%");
  });

  it("shows the empty label when every segment is zero", () => {
    render(
      <SegmentedBar
        segments={[{ key: "a", label: "A", value: 0, tone: "low" }]}
        emptyLabel="Nothing here."
      />,
    );

    expect(screen.getByText("Nothing here.")).toBeInTheDocument();
  });
});

describe("ProgressRing", () => {
  it("reports the percentage", () => {
    render(<ProgressRing value={1} total={4} label="Coverage" />);

    expect(screen.getByText("25%")).toBeInTheDocument();
    expect(screen.getByLabelText("Coverage: 1 of 4 (25%)")).toBeInTheDocument();
  });

  it("renders 0% rather than dividing by zero", () => {
    render(<ProgressRing value={0} total={0} label="Coverage" />);

    expect(screen.getByText("0%")).toBeInTheDocument();
  });

  it("clamps above 100%", () => {
    render(<ProgressRing value={9} total={4} label="Coverage" />);

    expect(screen.getByText("100%")).toBeInTheDocument();
  });
});
