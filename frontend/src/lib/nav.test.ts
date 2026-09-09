import { describe, it, expect } from "vitest";
import { DROP_PERMISSIONS, PERMISSIONS, type PermissionKey } from "@/lib/nav";

describe("nav permission constants", () => {
  it("defines the canonical nav-relevant permission keys", () => {
    expect(PERMISSIONS.alertsRead).toBe("alerts:read");
    expect(PERMISSIONS.alertsReview).toBe("alerts:review");
    expect(PERMISSIONS.athletesRead).toBe("athletes:read");
    expect(PERMISSIONS.investigationsRead).toBe("investigations:read");
    expect(PERMISSIONS.usersManage).toBe("users:manage");
  });

  it("keeps every drop-down permission aligned with a canonical key", () => {
    const canonical = new Set(Object.values(PERMISSIONS));
    for (const key of Object.values(DROP_PERMISSIONS)) {
      expect(canonical.has(key)).toBe(true);
    }
  });

  it("exposes a valid PermissionKey type union", () => {
    const keys: PermissionKey[] = [PERMISSIONS.alertsRead, PERMISSIONS.reportsGenerate];
    expect(keys).toHaveLength(2);
  });
});