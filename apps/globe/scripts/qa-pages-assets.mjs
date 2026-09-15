#!/usr/bin/env node
// ULTRONE-owned deployment check: every asset the static build asks for must
// exist in the directory the Pages deployment stages.
//
// .github/workflows/pages.yml mounts the *contents* of apps/globe/dist/ at
// /ultrone/globe/, so a document reference resolves like this:
//
//   <script src="cesium/Cesium.js">                    -> <site>/cesium/Cesium.js
//   <link href="./assets/index-abc.js">                -> <site>/assets/index-abc.js
//   <link href="/ultrone/globe/assets/index-abc.css">  -> <site>/assets/index-abc.css
//
// The third form is what an absolute Vite `base` emits. It is accepted (and
// re-rooted onto the staged site) so the check holds for either base style,
// but a root-absolute reference that falls *outside* the deployed subpath —
// e.g. "/logo.svg" loaded from a Pages project site — is a failure: it resolves
// above the site root and 404s in production. That is how the Cesium runtime
// went missing: vite-plugin-cesium mirrors `base` into both the emitted URLs
// and the output directory, so base "/ultrone/globe/" copied the runtime to
// dist/ultrone/globe/cesium/ while the document asked for /ultrone/globe/cesium.
//
// Usage:
//   node scripts/qa-pages-assets.mjs                                  # dist/
//   npm run qa:pages-assets
//   node scripts/qa-pages-assets.mjs --dist site/globe --prefix /ultrone/globe/
import { readdir, readFile, stat } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

/** Subpath the Pages deployment serves the globe build from. */
export const PAGES_PREFIX = '/ultrone/globe/';

/** Attributes a browser fetches while loading the document. */
const ASSET_ATTRIBUTES = new Set(['src', 'href']);

/** Entries that must ship for the console to boot. */
export const REQUIRED_ASSETS = [
  'index.html',
  'cesium/Cesium.js',
  'cesium/Widgets/widgets.css',
  'cesium/Workers',
  'cesium/Assets',
  'ultrone-demo-snapshot.json',
];

const TAG_PATTERN = /<([a-zA-Z][\w-]*)\b([^>]*)>/g;
const ATTRIBUTE_PATTERN = /([\w:-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')/g;

/** Normalize a site prefix to a leading and trailing slash. */
export function normalizePrefix(prefix = PAGES_PREFIX) {
  const trimmed = String(prefix).trim();
  if (!trimmed || trimmed === '/') return '/';
  return `/${trimmed.replace(/^\/+|\/+$/g, '')}/`;
}

/** Collect the fetchable references of a document in source order. */
export function collectAssetReferences(html) {
  const references = [];
  for (const tag of String(html).matchAll(TAG_PATTERN)) {
    const [, name, attributes] = tag;
    for (const attribute of attributes.matchAll(ATTRIBUTE_PATTERN)) {
      const key = attribute[1].toLowerCase();
      if (!ASSET_ATTRIBUTES.has(key)) continue;
      const value = attribute[2] ?? attribute[3] ?? '';
      references.push({ tag: name.toLowerCase(), attribute: key, value });
    }
  }
  return references;
}

/**
 * Map a document reference onto the staged site directory.
 * Returns `{ kind: 'external' }` for other origins, `{ kind: 'outside' }` for a
 * root-absolute path above the deployed subpath, and `{ kind: 'local', path }`
 * for a reference the deployment is expected to serve.
 */
export function resolveAssetReference(reference, prefix = PAGES_PREFIX) {
  const value = String(reference).trim();
  if (!value || value.startsWith('#')) return { kind: 'external' };
  if (/^[a-z][a-z0-9+.-]*:/i.test(value)) return { kind: 'external' };
  if (value.startsWith('//')) return { kind: 'external' };

  const withoutQuery = value.split(/[?#]/)[0];
  if (!withoutQuery) return { kind: 'external' };

  const root = normalizePrefix(prefix);
  let relative = withoutQuery;
  if (withoutQuery.startsWith('/')) {
    if (root === '/') {
      relative = withoutQuery.replace(/^\/+/, '');
    } else if (withoutQuery.startsWith(root)) {
      relative = withoutQuery.slice(root.length);
    } else {
      return { kind: 'outside', reference: value, prefix: root };
    }
  }

  const normalized = path.posix.normalize(relative);
  if (
    !normalized ||
    normalized === '.' ||
    normalized === '..' ||
    normalized.startsWith('../') ||
    path.posix.isAbsolute(normalized)
  ) {
    return { kind: 'outside', reference: value, prefix: root };
  }
  return { kind: 'local', path: normalized };
}

/** Directory a base-mirroring Cesium copy would nest the runtime in. */
export function nestedCesiumDirectory(prefix = PAGES_PREFIX) {
  return `${normalizePrefix(prefix).replace(/^\/+|\/+$/g, '')}/cesium`;
}

async function describe(target) {
  try {
    const info = await stat(target);
    if (info.isDirectory()) {
      const entries = await readdir(target);
      return { exists: true, directory: true, entries: entries.length };
    }
    return { exists: true, directory: false, entries: 1 };
  } catch {
    return { exists: false, directory: false, entries: 0 };
  }
}

/**
 * Verify the staged globe build resolves every asset it references.
 * Returns `{ siteDir, references, checked, failures }`; callers decide whether
 * a non-empty `failures` list is fatal.
 */
export async function verifyPagesAssets({
  siteDir,
  prefix = PAGES_PREFIX,
  required = REQUIRED_ASSETS,
  forbidden = [nestedCesiumDirectory(prefix)],
} = {}) {
  const root = path.resolve(siteDir ?? 'dist');
  const failures = [];
  const rootInfo = await describe(root);
  if (!rootInfo.exists || !rootInfo.directory) {
    return {
      siteDir: root,
      references: 0,
      checked: 0,
      failures: [`staged site directory is missing: ${root}`],
    };
  }

  for (const name of required) {
    const info = await describe(path.join(root, name));
    if (!info.exists) failures.push(`missing required asset: ${name}`);
    else if (info.directory && info.entries === 0)
      failures.push(`required asset directory is empty: ${name}`);
  }

  for (const name of forbidden) {
    if ((await describe(path.join(root, name))).exists)
      failures.push(
        `asset directory leaked below the site root: ${name} ` +
          '(the deployment only serves the contents of the build output)',
      );
  }

  const entry = path.join(root, 'index.html');
  const html = await readFile(entry, 'utf8').catch(() => '');
  const references = collectAssetReferences(html);
  let checked = 0;
  for (const reference of references) {
    const resolved = resolveAssetReference(reference.value, prefix);
    if (resolved.kind === 'external') continue;
    if (resolved.kind === 'outside') {
      failures.push(
        `root-absolute reference escapes the deployed prefix ` +
          `(${resolved.prefix}): ${reference.tag}[${reference.attribute}]="${reference.value}"`,
      );
      continue;
    }
    checked += 1;
    if (!(await describe(path.join(root, resolved.path))).exists)
      failures.push(
        `referenced asset is not in the build: ${resolved.path} ` +
          `(${reference.tag}[${reference.attribute}]="${reference.value}")`,
      );
  }

  return { siteDir: root, references: references.length, checked, failures };
}

/** Parse `--flag value` arguments, rejecting anything unrecognized. */
export function parseArguments(argv) {
  const options = { siteDir: 'dist', prefix: PAGES_PREFIX };
  for (let index = 0; index < argv.length; index += 1) {
    const flag = argv[index];
    if (flag === '--help' || flag === '-h') {
      options.help = true;
      continue;
    }
    const value = argv[index + 1];
    if (flag === '--dist' && value) options.siteDir = value;
    else if (flag === '--prefix' && value) options.prefix = value;
    else throw new Error(`Unknown argument: ${flag}`);
    index += 1;
  }
  return options;
}

const USAGE =
  'usage: node scripts/qa-pages-assets.mjs [--dist <dir>] [--prefix </subpath/>]';

const invoked = process.argv[1]
  ? pathToFileURL(path.resolve(process.argv[1])).href
  : '';
if (import.meta.url === invoked) {
  try {
    const options = parseArguments(process.argv.slice(2));
    if (options.help) {
      console.log(USAGE);
    } else {
      const result = await verifyPagesAssets(options);
      if (result.failures.length) {
        for (const failure of result.failures)
          console.error(`Pages asset check failed: ${failure}`);
        console.error(
          `${USAGE}\nchecked ${result.checked}/${result.references} references in ${result.siteDir}`,
        );
        process.exitCode = 1;
      } else {
        console.log(
          `Pages asset check passed: ${result.checked}/${result.references} ` +
            `references resolve in ${path.relative(process.cwd(), result.siteDir) || '.'}`,
        );
      }
    }
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
