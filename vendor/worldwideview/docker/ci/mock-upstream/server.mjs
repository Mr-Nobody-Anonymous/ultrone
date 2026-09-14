import { createServer } from "node:http";
import { readFileSync, existsSync } from "node:fs";
import { resolve, join } from "node:path";

const FIXTURE_DIR = process.env.FIXTURE_DIR ?? "/fixtures";
const PORT = Number(process.env.PORT ?? 8080);
const ROUTES_FILE = process.env.ROUTES_FILE ?? join(FIXTURE_DIR, "routes.json");

if (!existsSync(ROUTES_FILE)) {
  console.error(`[mock-upstream] no routes file at ${ROUTES_FILE}`);
  process.exit(1);
}

let routes;
try {
  routes = JSON.parse(readFileSync(ROUTES_FILE, "utf8"));
} catch (err) {
  console.error(`[mock-upstream] failed to parse ${ROUTES_FILE}:`, err);
  process.exit(1);
}

console.log(`[mock-upstream] loaded ${Object.keys(routes).length} routes from ${ROUTES_FILE}`);

createServer((req, res) => {
  const path = req.url?.split("?")[0] ?? "/";
  if (path === "/__health") {
    res.statusCode = 200;
    res.setHeader("content-type", "application/json");
    res.end(JSON.stringify({ status: "ok" }));
    return;
  }
  const file = routes[path];
  if (!file) {
    console.warn(`[mock-upstream] 404 ${req.method} ${path}`);
    res.statusCode = 404;
    res.setHeader("content-type", "application/json");
    res.end(JSON.stringify({ error: "no fixture", path }));
    return;
  }

  const filePath = resolve(FIXTURE_DIR, file);
  if (!filePath.startsWith(resolve(FIXTURE_DIR))) {
    res.statusCode = 400;
    res.end("bad fixture path");
    return;
  }

  try {
    const body = readFileSync(filePath);
    res.statusCode = 200;
    res.setHeader("content-type", file.endsWith(".json") ? "application/json" : "text/plain");
    res.end(body);
    console.log(`[mock-upstream] 200 ${req.method} ${path} -> ${file}`);
  } catch (err) {
    console.error(`[mock-upstream] 500 ${req.method} ${path}:`, err);
    res.statusCode = 500;
    res.end("fixture read failed");
  }
}).listen(PORT, () => {
  console.log(`[mock-upstream] listening on :${PORT}`);
});
