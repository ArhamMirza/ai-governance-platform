import { describe, expect, it, vi } from "vitest";

import { httpClient } from "../../../shared/api/httpClient";
import { aiSystemInventoryAdapter } from "../api";

vi.mock("../../../shared/api/httpClient", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../../shared/api/httpClient")>();
  return {
    ...actual,
    httpClient: {
      get: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
      delete: vi.fn(),
      postForm: vi.fn(),
    },
  };
});

describe("aiSystemInventoryAdapter", () => {
  it("get fetches the singleton sheet", async () => {
    await aiSystemInventoryAdapter.get();

    expect(httpClient.get).toHaveBeenCalledWith("/ai-system-inventory");
  });

  it("setColumns PUTs the new column list", async () => {
    const columns = [{ key: "name", label: "Name", data_type: "text" }];

    await aiSystemInventoryAdapter.setColumns(columns);

    expect(httpClient.put).toHaveBeenCalledWith("/ai-system-inventory/columns", { columns });
  });

  it("addRow POSTs the row data", async () => {
    await aiSystemInventoryAdapter.addRow({ name: "Resume Screener" });

    expect(httpClient.post).toHaveBeenCalledWith("/ai-system-inventory/rows", {
      data: { name: "Resume Screener" },
    });
  });

  it("updateRow PUTs to the row-specific endpoint", async () => {
    await aiSystemInventoryAdapter.updateRow(5, { risk_tier: "high" });

    expect(httpClient.put).toHaveBeenCalledWith("/ai-system-inventory/rows/5", {
      data: { risk_tier: "high" },
    });
  });

  it("deleteRow DELETEs the row-specific endpoint", async () => {
    await aiSystemInventoryAdapter.deleteRow(5);

    expect(httpClient.delete).toHaveBeenCalledWith("/ai-system-inventory/rows/5");
  });

  it("upload sends the file as form data", async () => {
    const file = new File(["name,risk_tier"], "inventory.csv", { type: "text/csv" });

    await aiSystemInventoryAdapter.upload(file);

    expect(httpClient.postForm).toHaveBeenCalledWith(
      "/ai-system-inventory/upload",
      expect.any(FormData),
    );
    const formData = vi.mocked(httpClient.postForm).mock.calls[0][1] as FormData;
    expect(formData.get("file")).toBe(file);
  });

  it("exportUrl points at the export endpoint", () => {
    expect(aiSystemInventoryAdapter.exportUrl()).toMatch(/\/ai-system-inventory\/export$/);
  });
});
