import { describe, it, expect } from "vitest";
import { validatePayloadValue, validatePayloadString } from "./payloadShape.js";

describe("validatePayloadValue", () => {
  it("accepts a non-empty GeoEntity array", () => {
    expect(validatePayloadValue([{ id: "a" }])).toEqual({ ok: true, shape: "geo-entity-array" });
  });
  it("rejects an empty array", () => {
    expect(validatePayloadValue([])).toEqual({ ok: false, reason: "GeoEntity[] is empty" });
  });
  it("accepts a non-empty items object", () => {
    expect(validatePayloadValue({ items: [1] })).toEqual({ ok: true, shape: "items-object" });
  });
  it("rejects an empty items array", () => {
    expect(validatePayloadValue({ items: [] })).toEqual({ ok: false, reason: "items[] is empty" });
  });
  it("accepts a single named collection", () => {
    expect(validatePayloadValue({ quakes: [1, 2] })).toEqual({ ok: true, shape: "named-collection" });
  });
  it("rejects an object with no array field", () => {
    const r = validatePayloadValue({ a: 1, b: 2 });
    expect(r.ok).toBe(false);
  });
  it("rejects a non-object, non-array value", () => {
    const r = validatePayloadValue(42);
    expect(r.ok).toBe(false);
  });
});

describe("validatePayloadString", () => {
  it("parses then validates", () => {
    expect(validatePayloadString('[{"id":"x"}]')).toEqual({ ok: true, shape: "geo-entity-array" });
  });
  it("rejects invalid JSON", () => {
    const r = validatePayloadString("{not json");
    expect(r.ok).toBe(false);
  });
});
