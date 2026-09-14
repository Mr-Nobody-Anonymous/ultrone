import { pathToFileURL } from "node:url";
import { resolve } from "node:path";

const KEBAB_RE = /^[a-z][a-z0-9]*(-[a-z0-9]+)*$/;

/**
 * Validates ADR-0002: a seeder's exported `name` field must be kebab-case
 * and (optionally) match an expected plugin id.
 *
 * @returns true if the contract holds; false (with stderr explanation) otherwise.
 */
export async function probeIdContract(opts: {
  seederDist: string;
  expectId?: string;
}): Promise<boolean> {
  const absPath = resolve(opts.seederDist);
  let mod: any;
  try {
    mod = await import(pathToFileURL(absPath).href);
  } catch (err) {
    console.error(`[id-contract] failed to import ${absPath}:`, err);
    return false;
  }

  const seeder = mod.default ?? mod;
  if (!seeder || typeof seeder !== "object") {
    console.error(`[id-contract] ${absPath} has no default export (or export is not an object)`);
    return false;
  }

  const name = seeder.name;
  if (typeof name !== "string" || name.length === 0) {
    console.error(`[id-contract] seeder default export missing required string field 'name'`);
    return false;
  }

  if (!KEBAB_RE.test(name)) {
    console.error(`[id-contract] seeder name "${name}" is not valid kebab-case (must match ${KEBAB_RE})`);
    return false;
  }

  if (opts.expectId && opts.expectId !== name) {
    console.error(
      `[id-contract] seeder name "${name}" does not match expected plugin id "${opts.expectId}" (ADR-0002 violation)`,
    );
    return false;
  }

  console.log(`[id-contract] OK — seeder name "${name}"${opts.expectId ? ` matches expected id` : ""}`);
  return true;
}
