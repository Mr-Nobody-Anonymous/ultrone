import * as Sentry from "@sentry/nextjs";
import { getEdition } from "@/core/edition";

export async function register() {
  const edition = getEdition();
  if (process.env.NEXT_RUNTIME === "nodejs") {
    if (!process.env.ENCRYPTION_MASTER_KEY && !process.env.MARKETPLACE_API_KEY) {
      throw new Error("[startup] ENCRYPTION_MASTER_KEY is not set. The server cannot start without it.");
    }
    if (!process.env.BETTER_AUTH_SECRET) {
      throw new Error("[startup] BETTER_AUTH_SECRET is not set. Better Auth requires it to sign session cookies. Generate one with `openssl rand -base64 32` and add `BETTER_AUTH_SECRET=<your-secret>` to your .env file. See .env.example for all required variables.");
    }
    if (edition === "demo" && !process.env.MARKETPLACE_API_KEY) {
      throw new Error("[startup] DEMO EDITION requires MARKETPLACE_API_KEY. Set it in env vars and restart.");
    }
    if (edition === "cloud" && process.env.MARKETPLACE_API_KEY) {
      console.warn(
        "[startup] WARNING: MARKETPLACE_API_KEY is set on edition=cloud. " +
        "All users will share the same credential. Unset this env var if unintended."
      );
    }
    if (process.env.MARKETPLACE_API_KEY && edition !== "demo" && edition !== "cloud") {
      console.log("[startup] Using MARKETPLACE_API_KEY credential source (env var path).");
    }
    await import("./sentry.server.config");
  }

  if (process.env.NEXT_RUNTIME === "edge") {
    await import("./sentry.edge.config");
  }
}

// Capture errors from Server Components, middleware, and proxies
export const onRequestError = Sentry.captureRequestError;
