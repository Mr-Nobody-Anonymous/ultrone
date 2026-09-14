import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/globeCommandQueue");
vi.mock("@/lib/mcpSessionCatalog");

// RED: ./filterTools does not exist yet. This import fails at collection time,
// locking the three-tool contract (set_filter, clear_filter, get_plugin_filters).
import { registerFilterTools } from "./filterTools";
import { enqueueGlobeCommand, resolveActiveSessionId } from "@/lib/globeCommandQueue";
import { readSessionCatalog } from "@/lib/mcpSessionCatalog";

const mockEnqueue = vi.mocked(enqueueGlobeCommand);
const mockResolveActiveSessionId = vi.mocked(resolveActiveSessionId);
const mockReadSessionCatalog = vi.mocked(readSessionCatalog);

const handlers: Record<string, (args: unknown) => unknown> = {};
const schemas: Record<string, { description: string }> = {};
const mockServer = {
    registerTool: vi.fn((name: string, schema: { description: string }, handler: (args: unknown) => unknown) => {
        handlers[name] = handler;
        schemas[name] = schema;
    }),
};

const ctx = { userId: "u1" };

function textOf(result: unknown): string {
    return (result as { content: Array<{ text: string }> }).content[0].text;
}

beforeEach(() => {
    vi.clearAllMocks();
    Object.keys(handlers).forEach((k) => delete handlers[k]);
    Object.keys(schemas).forEach((k) => delete schemas[k]);
    mockResolveActiveSessionId.mockResolvedValue("sess-abc");
    registerFilterTools(mockServer as never, ctx);
});

describe("filterTools tool descriptions (DESC-03)", () => {
    const toolNames = ["set_filter", "clear_filter", "get_plugin_filters"];

    it.each(toolNames)("%s description is non-empty and within 1024 chars", (name) => {
        const desc = schemas[name].description;
        expect(desc.length).toBeGreaterThan(0);
        expect(desc.length).toBeLessThanOrEqual(1024);
    });

    it.each(toolNames)("%s description contains 'Example:'", (name) => {
        expect(schemas[name].description).toContain("Example:");
    });

    it("get_plugin_filters description documents availability object shape", () => {
        const desc = schemas["get_plugin_filters"].description;
        expect(desc).toContain("available");
        expect(desc).toContain("no_session_active");
    });
});

describe("set_filter tool handler", () => {
    it("enqueues a setFilter command with pluginId and filters", async () => {
        await handlers["set_filter"]({
            pluginId: "flights",
            filters: { status: { type: "select", values: ["airborne"] } },
        });

        expect(mockEnqueue).toHaveBeenCalledWith(
            "u1",
            "sess-abc",
            { type: "setFilter", pluginId: "flights", filters: { status: { type: "select", values: ["airborne"] } } },
        );
    });

    it("returns NO_SESSION text and does not enqueue when no active session", async () => {
        mockResolveActiveSessionId.mockResolvedValue(null);

        const result = await handlers["set_filter"]({ pluginId: "flights", filters: {} });

        expect(textOf(result)).toMatch(/no active globe session/i);
        expect(mockEnqueue).not.toHaveBeenCalled();
    });
});

describe("clear_filter tool handler", () => {
    it("enqueues clearFilter without a pluginId field when pluginId omitted", async () => {
        await handlers["clear_filter"]({});

        expect(mockEnqueue).toHaveBeenCalledWith("u1", "sess-abc", { type: "clearFilter" });
    });

    it("enqueues clearFilter with pluginId when provided", async () => {
        await handlers["clear_filter"]({ pluginId: "flights" });

        expect(mockEnqueue).toHaveBeenCalledWith("u1", "sess-abc", { type: "clearFilter", pluginId: "flights" });
    });
});

describe("get_plugin_filters tool handler", () => {
    it("returns { available: true, filters: [...] } when plugin is loaded with filters", async () => {
        const defs = [{ id: "status", label: "Status", type: "select", propertyKey: "status" }];
        mockReadSessionCatalog.mockResolvedValue({
            tools: [],
            capabilities: [],
            filterDefinitions: { flights: defs },
        } as never);

        const result = await handlers["get_plugin_filters"]({ pluginId: "flights" });
        const parsed = JSON.parse(textOf(result));

        expect(parsed).toEqual({ available: true, filters: defs });
    });

    it("returns { available: false, reason: 'no_session_active' } when no active session", async () => {
        mockResolveActiveSessionId.mockResolvedValue(null);

        const result = await handlers["get_plugin_filters"]({ pluginId: "flights" });
        const parsed = JSON.parse(textOf(result));

        expect(parsed).toEqual({ available: false, reason: "no_session_active" });
    });

    it("returns { available: false, reason: 'plugin not loaded' } when plugin key absent from catalog", async () => {
        mockReadSessionCatalog.mockResolvedValue({
            tools: [],
            capabilities: [],
            filterDefinitions: {},
        } as never);

        const result = await handlers["get_plugin_filters"]({ pluginId: "flights" });
        const parsed = JSON.parse(textOf(result));

        expect(parsed).toEqual({ available: false, reason: "plugin not loaded" });
    });

    it("returns { available: true, filters: [] } when plugin is loaded but declares no filters", async () => {
        mockReadSessionCatalog.mockResolvedValue({
            tools: [],
            capabilities: [],
            filterDefinitions: { flights: [] },
        } as never);

        const result = await handlers["get_plugin_filters"]({ pluginId: "flights" });
        const parsed = JSON.parse(textOf(result));

        expect(parsed).toEqual({ available: true, filters: [] });
    });
});
