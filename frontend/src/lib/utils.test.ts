import { describe, it, expect } from "vitest";
import {
  cn,
  clamp,
  titleCase,
  initialsOf,
  truncate,
  formatScore,
  formatIso,
  formatDate,
  timeAgo,
  formatBytes,
  sortedKeys,
  formatPercent,
} from "@/lib/utils";

describe("cn", () => {
  it("merges conflicting tailwind classes, keeping the last", () => {
    expect(cn("px-2", "px-4")).toBe("px-4");
  });

  it("drops falsy values", () => {
    expect(cn("a", false, null, undefined, "b")).toBe("a b");
  });
});

describe("clamp", () => {
  it("clamps to the inclusive range", () => {
    expect(clamp(0.5, 0, 1)).toBe(0.5);
    expect(clamp(-1, 0, 1)).toBe(0);
    expect(clamp(9, 0, 1)).toBe(1);
  });
});

describe("titleCase", () => {
  it("splits on underscores and spaces", () => {
    expect(titleCase("very_high")).toBe("Very High");
    expect(titleCase("false positive")).toBe("False Positive");
  });

  it("handles empty input", () => {
    expect(titleCase("")).toBe("");
  });
});

describe("initialsOf", () => {
  it("takes up to two initials, uppercased", () => {
    expect(initialsOf("Tomas Abramson")).toBe("TA");
    expect(initialsOf("A")).toBe("A");
  });

  it("falls back to a placeholder for empty input", () => {
    expect(initialsOf("")).toBe("?");
    expect(initialsOf(null)).toBe("?");
    expect(initialsOf(undefined)).toBe("?");
  });
});

describe("truncate", () => {
  it("returns short strings unchanged", () => {
    expect(truncate("abc", 5)).toBe("abc");
  });

  it("truncates longer strings with an ellipsis", () => {
    expect(truncate("abcdefgh", 5)).toBe("abcd…");
  });
});

describe("formatScore", () => {
  it("drops a zero fractional part", () => {
    expect(formatScore(84)).toBe("84");
    expect(formatScore(84.5)).toBe("84.5");
  });
});

describe("formatIso", () => {
  it("renders a human-readable local timestamp", () => {
    const out = formatIso("2026-01-15T10:30:00Z");
    expect(out).not.toBe("—");
    expect(out).toContain("2026");
  });

  it("passes through invalid or empty values", () => {
    expect(formatIso(null)).toBe("—");
    expect(formatIso("not-a-date")).toBe("not-a-date");
  });
});

describe("formatDate", () => {
  it("handles date-only strings (YYYY-MM-DD)", () => {
    const out = formatDate("2026-03-04");
    expect(out).toContain("2026");
  });

  it("returns an em dash placeholder for empty input", () => {
    expect(formatDate("")).toBe("—");
  });
});

describe("timeAgo", () => {
  it("reports recent and older offsets", () => {
    expect(timeAgo(new Date().toISOString())).toBe("just now");
    expect(timeAgo(new Date(Date.now() - 1000 * 60).toISOString())).toBe("1m ago");
    expect(timeAgo(new Date(Date.now() - 1000 * 60 * 60 * 5).toISOString())).toBe("5h ago");
    expect(timeAgo(new Date(Date.now() - 1000 * 60 * 60 * 24 * 3).toISOString())).toBe("3d ago");
  });
});

describe("formatBytes", () => {
  it("formats byte sizes compactly", () => {
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(2048)).toBe("2.0 KB");
    expect(formatBytes(3 * 1024 * 1024)).toBe("3.0 MB");
  });
});

describe("sortedKeys", () => {
  it("sorts numeric entries descending", () => {
    expect(sortedKeys({ a: 1, b: 9, c: 4 })).toEqual([
      ["b", 9],
      ["c", 4],
      ["a", 1],
    ]);
  });
});

describe("formatPercent", () => {
  it("computes rounded percentages and guards zero denomators", () => {
    expect(formatPercent(3, 4)).toBe("75%");
    expect(formatPercent(1, 3)).toBe("33%");
    expect(formatPercent(5, 0)).toBe("0%");
  });
});