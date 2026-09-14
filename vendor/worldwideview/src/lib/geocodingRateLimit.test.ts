import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/redis");

import { checkRateLimit } from "./geocodingRateLimit";
import { redis } from "@/lib/redis";

const mockRedis = vi.mocked(redis, true);

beforeEach(() => {
    vi.clearAllMocks();
    mockRedis.zremrangebyscore.mockResolvedValue(0);
    mockRedis.zadd.mockResolvedValue(1);
    mockRedis.expire.mockResolvedValue(1);
});

describe("checkRateLimit", () => {
    it("resolves without error when zcard returns 1 (within limit of MAX_REQUESTS=1)", async () => {
        mockRedis.zcard.mockResolvedValue(1);

        const result = await checkRateLimit("u1");

        expect(result).toBeUndefined();
    });

    it("returns rate_limited error object when zcard returns 2 (exceeds MAX_REQUESTS=1)", async () => {
        mockRedis.zcard.mockResolvedValue(2);

        const result = await checkRateLimit("u1");

        expect(result).toMatchObject({ error: "rate_limited" });
    });

    it("calls zremrangebyscore to prune expired entries before checking count", async () => {
        mockRedis.zcard.mockResolvedValue(0);

        await checkRateLimit("u1");

        expect(mockRedis.zremrangebyscore).toHaveBeenCalledWith(
            expect.stringContaining("u1"),
            "-inf",
            expect.any(Number),
        );
    });

    it("calls zadd to record the current request timestamp", async () => {
        mockRedis.zcard.mockResolvedValue(0);

        await checkRateLimit("u1");

        expect(mockRedis.zadd).toHaveBeenCalledWith(
            expect.stringContaining("u1"),
            expect.any(Number),
            expect.any(String),
        );
    });

    it("calls expire(key, 5) to auto-expire the sorted set", async () => {
        mockRedis.zcard.mockResolvedValue(0);

        await checkRateLimit("u1");

        expect(mockRedis.expire).toHaveBeenCalledWith(expect.stringContaining("u1"), 5);
    });
});
