/**
 * @file freshness.test.ts
 * @description Unit tests for the skew-safe data-freshness helper.
 */

import { describe, expect, it } from "vitest";
import { getFreshness } from "./freshness";

const NOW = Date.parse("2026-01-15T12:00:00Z");

describe("getFreshness", () => {
    it("returns null when fetchedAt is missing", () => {
        expect(getFreshness(undefined, NOW)).toBeNull();
        expect(getFreshness(null, NOW)).toBeNull();
        expect(getFreshness("", NOW)).toBeNull();
    });

    it("returns null for unparseable timestamps (graceful degradation)", () => {
        expect(getFreshness("not-a-date", NOW)).toBeNull();
    });

    it("labels recent data as fresh", () => {
        const info = getFreshness("2026-01-15T11:58:00Z", NOW);
        expect(info?.tier).toBe("fresh");
        expect(info?.label).toBe("11:58:00Z");
    });

    it("labels 5-15 minute old data as aging", () => {
        expect(getFreshness("2026-01-15T11:50:00Z", NOW)?.tier).toBe("aging");
    });

    it("labels data older than 15 minutes as stale", () => {
        expect(getFreshness("2026-01-15T11:00:00Z", NOW)?.tier).toBe("stale");
    });

    it("treats server clock ahead of client (negative age) as fresh, not an error", () => {
        const info = getFreshness("2026-01-15T12:09:00Z", NOW);
        expect(info?.tier).toBe("fresh");
        expect(info?.label).toBe("12:09:00Z");
    });

    it("never lets small skew flip the tier near a threshold", () => {
        // 4m50s old: even 60s of skew keeps it under the 5m fresh threshold.
        expect(getFreshness("2026-01-15T11:55:10Z", NOW)?.tier).toBe("fresh");
        // 14m59s old: 60s of skew keeps it under the 15m aging threshold.
        expect(getFreshness("2026-01-15T11:45:01Z", NOW)?.tier).toBe("aging");
    });

    it("formats the label from the server timestamp in UTC", () => {
        const info = getFreshness("2026-01-15T09:03:27Z", NOW);
        expect(info?.label).toBe("09:03:27Z");
        expect(info?.title).toContain("2026-01-15T09:03:27.000Z");
    });
});
