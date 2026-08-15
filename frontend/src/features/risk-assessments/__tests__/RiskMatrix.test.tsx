import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { SheetRow } from "../../sheets/types";
import { RiskMatrix } from "../components/RiskMatrix";

function makeRow(id: number, data: Record<string, unknown>): SheetRow {
  return {
    id,
    sheet_id: 1,
    row_index: id,
    data,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
}

describe("RiskMatrix", () => {
  it("counts a row into the correct likelihood/impact cell", () => {
    render(<RiskMatrix rows={[makeRow(1, { likelihood: 3, impact: 4 })]} />);

    expect(screen.getByLabelText("Likelihood 3, Impact 4, 1 risk(s)")).toHaveTextContent("1");
  });

  it("aggregates multiple rows landing on the same cell", () => {
    render(
      <RiskMatrix
        rows={[
          makeRow(1, { likelihood: 5, impact: 5 }),
          makeRow(2, { likelihood: 5, impact: 5 }),
        ]}
      />,
    );

    expect(screen.getByLabelText("Likelihood 5, Impact 5, 2 risk(s)")).toHaveTextContent("2");
  });

  it("ignores rows missing likelihood or impact", () => {
    render(<RiskMatrix rows={[makeRow(1, { category: "Bias" })]} />);

    expect(screen.getByLabelText("Likelihood 1, Impact 1, 0 risk(s)")).toHaveTextContent("");
  });

  it("clamps out-of-range values into the 1-5 grid", () => {
    render(<RiskMatrix rows={[makeRow(1, { likelihood: 9, impact: 0 })]} />);

    expect(screen.getByLabelText("Likelihood 5, Impact 1, 1 risk(s)")).toHaveTextContent("1");
  });

  it("renders an empty matrix with no rows", () => {
    render(<RiskMatrix rows={[]} />);

    expect(screen.getByText("Risk Matrix (Likelihood × Impact)")).toBeInTheDocument();
  });
});
