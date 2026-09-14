import { describe, it, expect, beforeEach } from "vitest";
import { createStore, type StoreApi } from "zustand/vanilla";
import { createSeederHealthSlice, normalizeSeederHealth, type SeederHealthSlice } from "./seederHealthSlice";

type MockAppStore = SeederHealthSlice;

describe("seederHealthSlice", () => {
    let store: StoreApi<MockAppStore>;

    beforeEach(() => {
        store = createStore<MockAppStore>((set, get, api) => ({
            ...createSeederHealthSlice(set as never, get as never, api as never),
        }));
    });

    it("starts with an empty map", () => {
        expect(store.getState().seederHealth).toEqual({});
    });

    it("merges a raw delta over an existing entry", () => {
        store.getState().updateSeederHealth("aviation", {
            lastRun: 1700000000000,
            stale: false,
            intervalMs: 60000,
        });

        store.getState().updateSeederHealth("aviation", {
            stale: true,
            lastError: "boom",
            bogusField: "dropped",
        });

        const entry = store.getState().seederHealth["aviation"];
        expect(entry.lastRun).toBe(1700000000000);
        expect(entry.stale).toBe(true);
        expect(entry.lastError).toBe("boom");
        expect(entry.intervalMs).toBe(60000);
        expect((entry as unknown as Record<string, unknown>).bogusField).toBeUndefined();
    });

    it("replaces the whole map via setSeederHealth", () => {
        store.getState().setSeederHealth({
            aviation: normalizeSeederHealth("aviation", { stale: true, lastRun: 1 }),
        });
        expect(store.getState().seederHealth["aviation"].stale).toBe(true);
    });
});

describe("normalizeSeederHealth", () => {
    it("defaults missing fields and drops unknown fields", () => {
        const out = normalizeSeederHealth("marine", { stale: true });
        expect(out).toEqual({
            pluginId: "marine",
            lastRun: null,
            lastError: null,
            failureCount: 0,
            intervalMs: null,
            cron: null,
            expectedMaxAgeMs: null,
            stale: true,
        });
    });

    it("coerces non-numeric lastRun to null", () => {
        const out = normalizeSeederHealth("x", { lastRun: "not-a-number" });
        expect(out.lastRun).toBeNull();
    });
});
