import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { resolveEdition, resolveServerEdition, getEdition } from "./edition";
import type { Edition } from "./edition";

describe("resolveEdition", () => {
    it("defaults to 'local' when env var is undefined", () => {
        expect(resolveEdition(undefined)).toBe("local");
    });

    it("defaults to 'local' for an empty string", () => {
        expect(resolveEdition("")).toBe("local");
    });

    it("returns 'local' for value 'local'", () => {
        expect(resolveEdition("local")).toBe("local");
    });

    it("returns 'cloud' for value 'cloud'", () => {
        expect(resolveEdition("cloud")).toBe("cloud");
    });

    it("returns 'demo' for value 'demo'", () => {
        expect(resolveEdition("demo")).toBe("demo");
    });

    it("is case-insensitive", () => {
        expect(resolveEdition("CLOUD")).toBe("cloud");
        expect(resolveEdition("Demo")).toBe("demo");
    });

    it("trims whitespace", () => {
        expect(resolveEdition("  cloud  ")).toBe("cloud");
    });

    it("falls back to 'local' for invalid values", () => {
        const invalid: string[] = ["staging", "production", "test", "123"];
        for (const val of invalid) {
            expect(resolveEdition(val)).toBe("local" satisfies Edition);
        }
    });
});

describe("resolveServerEdition (runtime resolution)", () => {
    const ORIGINAL_ENV = { ...process.env };

    beforeEach(() => {
        vi.resetModules();
        process.env = { ...ORIGINAL_ENV };
        delete process.env.WWV_EDITION;
        delete process.env.NEXT_PUBLIC_WWV_EDITION;
    });

    afterEach(() => {
        vi.unstubAllEnvs();
    });

    it("falls back to 'local' when no edition env var is set", async () => {
        const { resolveServerEdition: rs } = await import("./edition");
        expect(rs()).toBe("local");
    });

    it("uses the runtime WWV_EDITION when set", async () => {
        vi.stubEnv("WWV_EDITION", "demo");
        const { resolveServerEdition: rs } = await import("./edition");
        expect(rs()).toBe("demo");
    });

    it("lets the runtime WWV_EDITION override the build-time NEXT_PUBLIC_ bake", async () => {
        vi.stubEnv("NEXT_PUBLIC_WWV_EDITION", "cloud");
        vi.stubEnv("WWV_EDITION", "demo");
        const { resolveServerEdition: rs } = await import("./edition");
        expect(rs()).toBe("demo");
    });

    it("falls back to the NEXT_PUBLIC_ bake when WWV_EDITION is unset", async () => {
        vi.stubEnv("NEXT_PUBLIC_WWV_EDITION", "cloud");
        const { resolveServerEdition: rs } = await import("./edition");
        expect(rs()).toBe("cloud");
    });

    it("ignores an empty WWV_EDITION and falls back to the bake", async () => {
        vi.stubEnv("WWV_EDITION", "");
        vi.stubEnv("NEXT_PUBLIC_WWV_EDITION", "demo");
        const { resolveServerEdition: rs } = await import("./edition");
        expect(rs()).toBe("demo");
    });

    it("falls back to 'local' for an invalid runtime value", async () => {
        vi.stubEnv("WWV_EDITION", "staging");
        const { resolveServerEdition: rs } = await import("./edition");
        expect(rs()).toBe("local");
    });

    it("is case-insensitive and trims whitespace", async () => {
        vi.stubEnv("WWV_EDITION", "  CLOUD  ");
        const { resolveServerEdition: rs } = await import("./edition");
        expect(rs()).toBe("cloud");
    });

    it("getEdition() re-reads env on every call (request-time freshness)", async () => {
        vi.stubEnv("WWV_EDITION", "demo");
        const { getEdition: ge } = await import("./edition");
        expect(ge()).toBe("demo");
        vi.stubEnv("WWV_EDITION", "local");
        expect(ge()).toBe("local");
    });
});

describe("isHistoryEnabled (derived from edition)", () => {
    it("is disabled on demo edition", () => {
        // History unavailable on demo — shared credentials breach the non-transferable ToS clause
        expect(resolveEdition("demo")).toBe("demo");
        // Simulate the flag logic: !isDemo
        const historyEnabled = resolveEdition("demo") !== "demo";
        expect(historyEnabled).toBe(false);
    });

    it("is enabled on local edition", () => {
        const historyEnabled = resolveEdition("local") !== "demo";
        expect(historyEnabled).toBe(true);
    });

    it("is enabled on cloud edition", () => {
        const historyEnabled = resolveEdition("cloud") !== "demo";
        expect(historyEnabled).toBe(true);
    });
});
