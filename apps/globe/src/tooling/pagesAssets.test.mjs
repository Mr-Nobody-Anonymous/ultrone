import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import {
  PAGES_PREFIX,
  REQUIRED_ASSETS,
  collectAssetReferences,
  nestedCesiumDirectory,
  normalizePrefix,
  parseArguments,
  resolveAssetReference,
  verifyPagesAssets,
} from '../../scripts/qa-pages-assets.mjs';

/** Build a throwaway deployment directory that mirrors the Pages staging. */
async function fixture(t, files) {
  const root = await mkdtemp(path.join(tmpdir(), 'gev-pages-assets-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  for (const [name, contents] of Object.entries(files)) {
    const target = path.join(root, name);
    await mkdir(path.dirname(target), { recursive: true });
    if (contents === null) await mkdir(target, { recursive: true });
    else await writeFile(target, contents);
  }
  return root;
}

/** A staged build that satisfies every requirement of the checker. */
function healthyBuild(html) {
  return {
    'index.html':
      html ??
      '<script src="cesium/Cesium.js"></script><link href="cesium/Widgets/widgets.css">',
    'cesium/Cesium.js': 'window.Cesium = {};',
    'cesium/Widgets/widgets.css': '.cesium {}',
    'cesium/Workers/worker.js': '// worker',
    'cesium/Assets/approximateTerrainHeights.json': '{}',
    'ultrone-demo-snapshot.json': '{"count": 0}',
  };
}

test('prefixes normalize to a leading and trailing slash', () => {
  assert.equal(normalizePrefix('/ultrone/globe'), '/ultrone/globe/');
  assert.equal(normalizePrefix('ultrone/globe/'), '/ultrone/globe/');
  assert.equal(normalizePrefix('/'), '/');
  assert.equal(normalizePrefix(PAGES_PREFIX), PAGES_PREFIX);
});

test('only fetchable src and href attributes are collected', () => {
  const references = collectAssetReferences(
    `<link rel="icon" href="/logo.svg">
     <script src="./assets/index.js"></script>
     <img src="models/plane.glb" data-logo-src="/logo.svg" srcset="ignored.png 2x">
     <a href="#telemetry">jump</a>`,
  );
  assert.deepEqual(references, [
    { tag: 'link', attribute: 'href', value: '/logo.svg' },
    { tag: 'script', attribute: 'src', value: './assets/index.js' },
    { tag: 'img', attribute: 'src', value: 'models/plane.glb' },
    { tag: 'a', attribute: 'href', value: '#telemetry' },
  ]);
  assert.equal(
    references.some(
      (reference) =>
        reference.value === '/logo.svg' &&
        reference.attribute === 'data-logo-src',
    ),
    false,
  );
});

test('references resolve onto the staged site, relative or base-prefixed', () => {
  assert.deepEqual(resolveAssetReference('cesium/Cesium.js'), {
    kind: 'local',
    path: 'cesium/Cesium.js',
  });
  assert.deepEqual(resolveAssetReference('./assets/index.js'), {
    kind: 'local',
    path: 'assets/index.js',
  });
  assert.deepEqual(resolveAssetReference('/ultrone/globe/logo.svg'), {
    kind: 'local',
    path: 'logo.svg',
  });
  assert.deepEqual(resolveAssetReference('assets/../models/plane.glb?v=2'), {
    kind: 'local',
    path: 'models/plane.glb',
  });
});

test('non-assets are skipped and root-absolute escapes are reported', () => {
  assert.equal(resolveAssetReference('#telemetry').kind, 'external');
  assert.equal(
    resolveAssetReference('https://fonts.googleapis.com/css').kind,
    'external',
  );
  assert.equal(
    resolveAssetReference('data:image/svg+xml;base64,AA==').kind,
    'external',
  );
  assert.equal(
    resolveAssetReference('mailto:ops@example.com').kind,
    'external',
  );
  assert.equal(resolveAssetReference('').kind, 'external');
  assert.deepEqual(resolveAssetReference('/logo.svg'), {
    kind: 'outside',
    reference: '/logo.svg',
    prefix: PAGES_PREFIX,
  });
  assert.equal(
    resolveAssetReference('/ultrone/globe/../../secret.js').kind,
    'outside',
  );
});

test('a healthy staged build passes and reports what it checked', async (t) => {
  const root = await fixture(t, healthyBuild());
  const result = await verifyPagesAssets({ siteDir: root });
  assert.deepEqual(result.failures, []);
  assert.equal(result.checked, 2);
  assert.deepEqual(REQUIRED_ASSETS, [
    'index.html',
    'cesium/Cesium.js',
    'cesium/Widgets/widgets.css',
    'cesium/Workers',
    'cesium/Assets',
    'ultrone-demo-snapshot.json',
  ]);
});

test('the missing Cesium runtime and nested copy are both reported', async (t) => {
  const files = healthyBuild();
  delete files['cesium/Cesium.js'];
  delete files['cesium/Widgets/widgets.css'];
  delete files['cesium/Workers/worker.js'];
  files['cesium/Assets'] = null;
  delete files['cesium/Assets/approximateTerrainHeights.json'];
  files['ultrone/globe/cesium/Cesium.js'] = 'window.Cesium = {};';
  const root = await fixture(t, files);

  const result = await verifyPagesAssets({ siteDir: root });
  assert.deepEqual(result.failures, [
    'missing required asset: cesium/Cesium.js',
    'missing required asset: cesium/Widgets/widgets.css',
    'missing required asset: cesium/Workers',
    'required asset directory is empty: cesium/Assets',
    `asset directory leaked below the site root: ${nestedCesiumDirectory()}` +
      ' (the deployment only serves the contents of the build output)',
    'referenced asset is not in the build: cesium/Cesium.js (script[src]="cesium/Cesium.js")',
    'referenced asset is not in the build: cesium/Widgets/widgets.css (link[href]="cesium/Widgets/widgets.css")',
  ]);
});

test('a root-absolute asset above the deployed subpath fails the deployment', async (t) => {
  const root = await fixture(
    t,
    healthyBuild(
      '<link rel="icon" href="/logo.svg"><script src="cesium/Cesium.js"></script>',
    ),
  );
  const result = await verifyPagesAssets({ siteDir: root });
  assert.deepEqual(result.failures, [
    `root-absolute reference escapes the deployed prefix (${PAGES_PREFIX}): ` +
      'link[href]="/logo.svg"',
  ]);
  assert.equal(result.checked, 1);
});

test('a missing staged site fails instead of reporting success', async () => {
  const result = await verifyPagesAssets({ siteDir: 'does-not-exist' });
  assert.equal(result.checked, 0);
  assert.equal(result.failures.length, 1);
  assert.match(result.failures[0], /staged site directory is missing/);
});

test('the CLI accepts --dist and --prefix and rejects unknown flags', () => {
  assert.deepEqual(parseArguments([]), {
    siteDir: 'dist',
    prefix: PAGES_PREFIX,
  });
  assert.deepEqual(
    parseArguments(['--dist', 'site/globe', '--prefix', '/ultrone/globe/']),
    { siteDir: 'site/globe', prefix: '/ultrone/globe/' },
  );
  assert.equal(parseArguments(['--help']).help, true);
  assert.throws(() => parseArguments(['--verbose']), /Unknown argument/);
});
