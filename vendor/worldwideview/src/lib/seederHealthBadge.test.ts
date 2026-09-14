import { describe, it, expect } from "vitest";
import { deriveSeederBadge, deriveSeederChecklist } from "./seederHealthBadge";
import type { SeederHealth } from "@/core/state/seederHealthSlice";

function health(overrides: Partial<SeederHealth> = {}): SeederHealth {
    return {
        pluginId: "aviation",
        lastRun: 1700000000000,
        lastError: null,
        failureCount: 0,
        intervalMs: 60000,
        cron: null,
        expectedMaxAgeMs: 120000,
        stale: false,
        ...overrides,
    };
}

describe("deriveSeederBadge", () => {
    it("returns null when there is no health data (graceful)", () => {
        expect(deriveSeederBadge(undefined)).toBeNull();
        expect(deriveSeederBadge(null)).toBeNull();
    });

    it("reports error when lastError is set (priority over stale)", () => {
        const badge = deriveSeederBadge(health({ lastError: "boom", stale: true }));
        expect(badge).toEqual({
            state: "error",
            label: "error",
            title: "Seeder error: boom",
        });
    });

    it("reports stale when server says stale (server-computed only)", () => {
        const badge = deriveSeederBadge(health({ stale: true }));
        expect(badge?.state).toBe("stale");
    });

    it("reports live when fresh and error-free", () => {
        const badge = deriveSeederBadge(health());
        expect(badge?.state).toBe("live");
    });
});

describe("deriveSeederChecklist", () => {
    it("returns a no-telemetry row when health is missing", () => {
        const rows = deriveSeederChecklist(undefined);
        expect(rows).toHaveLength(1);
        expect(rows[0].id).toBe("no-telemetry");
    });

    it("flags never-ran, stale, error, and failures from the same health object", () => {
        const rows = deriveSeederChecklist(health({
            lastRun: null,
            stale: true,
            lastError: "timeout",
            failureCount: 4,
        }));
        const byId = Object.fromEntries(rows.map((r) => [r.id, r]));
        expect(byId["never-ran"].suspect).toBe(true);
        expect(byId["stale"].suspect).toBe(true);
        expect(byId["last-error"].suspect).toBe(true);
        expect(byId["failures"].suspect).toBe(true);
    });

    it("marks nothing as suspect for a healthy seeder", () => {
        const rows = deriveSeederChecklist(health());
        expect(rows.every((r) => r.suspect === false)).toBe(true);
    });
});
