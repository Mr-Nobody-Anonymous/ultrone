/**
 * Shared payload-shape validator for the WWV data contract (data-engine-architecture.md §7).
 * A valid live payload is one of three non-empty shapes:
 *  - geo-entity-array: a top-level non-empty array
 *  - items-object: an object with a non-empty `items` array
 *  - named-collection: an object whose single array-valued key is non-empty
 */
export type PayloadShape = "geo-entity-array" | "items-object" | "named-collection";

export type PayloadValidation =
  | { ok: true; shape: PayloadShape }
  | { ok: false; reason: string };

/**
 * Validate an already-parsed payload value.
 * @param p - parsed JSON value
 * @returns ok with the detected shape, or a reason for rejection
 */
export function validatePayloadValue(p: unknown): PayloadValidation {
  if (Array.isArray(p)) {
    return p.length > 0
      ? { ok: true, shape: "geo-entity-array" }
      : { ok: false, reason: "GeoEntity[] is empty" };
  }
  if (p && typeof p === "object") {
    const obj = p as Record<string, unknown>;
    if (Array.isArray(obj.items)) {
      return obj.items.length > 0
        ? { ok: true, shape: "items-object" }
        : { ok: false, reason: "items[] is empty" };
    }
    const arrayKeys = Object.keys(obj).filter((k) => Array.isArray(obj[k]));
    if (arrayKeys.length === 1) {
      const arr = obj[arrayKeys[0]] as unknown[];
      return arr.length > 0
        ? { ok: true, shape: "named-collection" }
        : { ok: false, reason: `${arrayKeys[0]}[] is empty` };
    }
    return {
      ok: false,
      reason: `payload object has no recognizable array field (keys: ${Object.keys(obj).join(", ")})`,
    };
  }
  return { ok: false, reason: `payload is neither array nor object (typeof=${typeof p})` };
}

/**
 * Parse a raw JSON string, then validate the resulting value's shape.
 * @param raw - raw JSON string from Redis
 */
export function validatePayloadString(raw: string): PayloadValidation {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (err) {
    return { ok: false, reason: `not valid JSON (${(err as Error).message})` };
  }
  return validatePayloadValue(parsed);
}
