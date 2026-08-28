import { describe, expect, it } from "vitest";

import { clockTime, relativeTime, rupees } from "./format";

describe("rupees", () => {
  it("converts paise to a rounded ₹ string", () => {
    expect(rupees(7499900)).toBe("₹74,999");
  });

  it("supports precise 2-decimal formatting", () => {
    expect(rupees(7499900, true)).toBe("₹74,999.00");
  });

  it("treats null/undefined as zero", () => {
    expect(rupees(null)).toBe("₹0");
    expect(rupees(undefined)).toBe("₹0");
  });

  it("never does math the backend should do — pure display of the given integer", () => {
    expect(rupees(150)).toBe("₹2"); // 150 paise -> ₹1.50 -> rounded ₹2
    expect(rupees(150, true)).toBe("₹1.50");
  });
});

describe("relativeTime", () => {
  it("reports very recent timestamps as 'just now'", () => {
    expect(relativeTime(new Date().toISOString())).toBe("just now");
  });

  it("reports minutes and hours", () => {
    expect(relativeTime(new Date(Date.now() - 5 * 60_000).toISOString())).toBe("5 min ago");
    expect(relativeTime(new Date(Date.now() - 3 * 3_600_000).toISOString())).toBe("3 hr ago");
  });

  it("reports days", () => {
    expect(relativeTime(new Date(Date.now() - 2 * 86_400_000).toISOString())).toBe("2 days ago");
  });
});

describe("clockTime", () => {
  it("formats an ISO string to HH:MM", () => {
    expect(clockTime("2026-08-27T09:05:00Z")).toMatch(/^\d{2}:\d{2}(\s?[AP]M)?$/i);
  });
});
