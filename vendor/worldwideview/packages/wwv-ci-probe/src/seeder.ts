import { Redis } from "ioredis";
import { validatePayloadString } from "./payloadShape.js";

/**
 * Polls Redis for `data:<name>:live` and validates that the seeder produced a
 * non-empty payload in one of the three accepted shapes (see
 * data-engine-architecture.md §7).
 *
 * @returns true if a valid payload arrived within the timeout; false otherwise.
 */
export async function probeSeeder(opts: {
  name: string;
  redisUrl: string;
  timeoutMs: number;
}): Promise<boolean> {
  const redis = new Redis(opts.redisUrl, { lazyConnect: true, maxRetriesPerRequest: 1 });
  const key = `data:${opts.name}:live`;
  const deadline = Date.now() + opts.timeoutMs;
  const pollIntervalMs = 1000;

  try {
    await redis.connect();
  } catch (err) {
    console.error(`[seeder] cannot connect to Redis at ${opts.redisUrl}:`, err);
    return false;
  }

  console.log(`[seeder] waiting for ${key} (timeout ${opts.timeoutMs}ms)`);

  while (Date.now() < deadline) {
    const raw = await redis.get(key);
    if (raw && raw.length > 0) {
      const validation = validatePayloadString(raw);
      await redis.quit();
      if (!validation.ok) {
        console.error(`[seeder] payload present but invalid: ${validation.reason}`);
        return false;
      }
      console.log(`[seeder] OK — ${key} populated (shape: ${validation.shape}, bytes: ${raw.length})`);
      return true;
    }
    await sleep(pollIntervalMs);
  }

  await redis.quit();
  console.error(`[seeder] timed out — ${key} never populated within ${opts.timeoutMs}ms`);
  return false;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
