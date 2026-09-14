import { describe, it, expect, afterEach } from "vitest";
import { WebSocketServer } from "ws";
import { probeWs } from "./ws.js";

let server: WebSocketServer | undefined;
afterEach(() => { server?.close(); server = undefined; });

function startEngine(opts: { pluginId: string; requireSubscribe: boolean }) {
  server = new WebSocketServer({ port: 0 });
  server.on("connection", (sock) => {
    sock.send(JSON.stringify({ type: "welcome", engine: "test", plugins: [opts.pluginId] }));
    const send = () =>
      sock.send(JSON.stringify({ type: "data", pluginId: opts.pluginId, payload: [{ id: "x" }] }));
    if (!opts.requireSubscribe) { setInterval(send, 20); return; }
    sock.on("message", (raw) => {
      const msg = JSON.parse(raw.toString());
      if (msg.action === "subscribe" && msg.pluginId === opts.pluginId) send();
    });
  });
  const addr = server.address();
  const port = typeof addr === "object" && addr ? addr.port : 0;
  return `ws://127.0.0.1:${port}/stream`;
}

describe("probeWs", () => {
  it("receives data from a subscribe-required engine (sends subscribe frame)", async () => {
    const url = startEngine({ pluginId: "stub", requireSubscribe: true });
    const ok = await probeWs({ name: "stub", wsUrl: url, timeoutMs: 3000 });
    expect(ok).toBe(true);
  });
  it("times out (false) when the plugin never produces data", async () => {
    const url = startEngine({ pluginId: "other", requireSubscribe: true });
    const ok = await probeWs({ name: "stub", wsUrl: url, timeoutMs: 800 });
    expect(ok).toBe(false);
  });
});
