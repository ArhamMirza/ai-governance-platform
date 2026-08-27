import { describe, expect, it } from "vitest";

import { hasPermission } from "../permissions";

describe("hasPermission", () => {
  it("lets a viewer view but nothing else", () => {
    expect(hasPermission("viewer", "view")).toBe(true);
    expect(hasPermission("viewer", "edit")).toBe(false);
    expect(hasPermission("viewer", "approve")).toBe(false);
    expect(hasPermission("viewer", "manage_users")).toBe(false);
  });

  it("lets a contributor view and edit but not approve or manage", () => {
    expect(hasPermission("contributor", "view")).toBe(true);
    expect(hasPermission("contributor", "edit")).toBe(true);
    expect(hasPermission("contributor", "approve")).toBe(false);
    expect(hasPermission("contributor", "manage_users")).toBe(false);
    expect(hasPermission("contributor", "manage_settings")).toBe(false);
  });

  it("lets an admin do everything", () => {
    expect(hasPermission("admin", "view")).toBe(true);
    expect(hasPermission("admin", "edit")).toBe(true);
    expect(hasPermission("admin", "approve")).toBe(true);
    expect(hasPermission("admin", "manage_users")).toBe(true);
    expect(hasPermission("admin", "manage_settings")).toBe(true);
  });

  it("permits nothing for an unrecognized or missing role", () => {
    expect(hasPermission("not-a-role", "view")).toBe(false);
    expect(hasPermission(undefined, "view")).toBe(false);
  });
});
