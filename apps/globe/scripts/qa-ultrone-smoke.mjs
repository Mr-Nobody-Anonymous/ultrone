// ULTRONE-owned smoke QA: boot the globe headless, assert the ULTRONE layer
// registers + renders tracks, capture a screenshot. Usage:
//   ULTRONE_GLOBE_URL=http://127.0.0.1:4173 node scripts/qa-ultrone-smoke.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import puppeteer from 'puppeteer';

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const shotsDir = path.join(root, '.qa-shots');
const baseUrl = process.env.ULTRONE_GLOBE_URL || 'http://127.0.0.1:4173';

const executablePath =
  process.env.PUPPETEER_EXECUTABLE_PATH ||
  (await puppeteer.executablePath().catch(() => null));
if (!executablePath || !fs.existsSync(executablePath)) {
  throw new Error('Puppeteer Chrome for Testing is unavailable');
}
fs.mkdirSync(shotsDir, { recursive: true });

const browser = await puppeteer.launch({
  headless: 'new',
  executablePath,
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--no-sandbox'],
});
const failures = [];
const consoleErrors = [];
try {
  const page = await browser.newPage();
  await page.setViewport({ width: 1600, height: 900 });
  page.on('console', (message) => {
    if (
      message.type() === 'error' &&
      !/Failed to load resource.*404/i.test(message.text())
    ) {
      consoleErrors.push(message.text());
    }
  });
  page.on('pageerror', (error) => consoleErrors.push(error.message));
  page.on('requestfailed', (req) =>
    consoleErrors.push(`requestfailed: ${req.url()} ${req.failure()?.errorText}`),
  );

  const check = (name, passed, detail = '') => {
    console.log(`  [${passed ? 'PASS' : 'FAIL'}] ${name}${detail ? ` — ${detail}` : ''}`);
    if (!passed) failures.push(name);
  };

  await page.goto(baseUrl, { waitUntil: 'networkidle2', timeout: 120000 });

  // App boot: the loading screen clears once Cesium + data layers init.
  await page
    .waitForFunction(
      () => {
        const loader = document.getElementById('loading-screen');
        return !loader || loader.style.display === 'none' || loader.hidden;
      },
      { timeout: 90000 },
    )
    .catch(() => {});
  check('page title is ULTRONE', (await page.title()).includes('ULTRONE'));

  // ULTRONE layer toggle exists in the data panel.
  const toggle = await page.evaluate(() => {
    const el = document.getElementById('data-toggles');
    return el ? el.textContent : null;
  });
  check(
    'ULTRONE layer registered in data toggles',
    typeof toggle === 'string' && toggle.includes('ULTRONE'),
    toggle ? `${toggle.length} chars of toggles` : 'no #data-toggles',
  );

  // Enable the ULTRONE layer via its toggle and wait for a proxied fetch.
  const apiResponse = page
    .waitForResponse(
      (res) => res.url().includes('/api/ultrone/entities') && res.ok(),
      { timeout: 30000 },
    )
    .catch(() => null);
  const toggled = await page.evaluate(() => {
    const el = document.getElementById('data-toggles');
    if (!el) return false;
    const items = [...el.querySelectorAll('input,button,[role="switch"],label')];
    const target = items.find((n) =>
      (n.textContent || n.value || n.getAttribute('aria-label') || '').includes(
        'ULTRONE',
      ),
    );
    const scope =
      target ||
      [...el.querySelectorAll('*')].find((n) =>
        (n.textContent || '').includes('ULTRONE Tracks'),
      );
    if (!scope) return false;
    (target || scope).click();
    return true;
  });
  check('ULTRONE toggle clickable', toggled);
  const res = await apiResponse;
  check('ULTRONE entities fetched through proxy', !!res);

  // Cesium canvas is rendering frames.
  const canvas = await page.$('canvas');
  check('cesium canvas present', !!canvas);
  await new Promise((r) => setTimeout(r, 8000));
  const shot = path.join(shotsDir, 'ultrone-globe.png');
  await page.screenshot({ path: shot });
  const bytes = fs.statSync(shot).size;
  check('screenshot captured', bytes > 50000, `${bytes} bytes`);

  const fatal = consoleErrors.filter(
    (e) =>
      !/cesium|ion|google|fonts\.g|sentry|favicon/i.test(e) &&
      !/WebGL|swiftshader|GPU/i.test(e),
  );
  check('no fatal console errors', fatal.length === 0, fatal.slice(0, 3).join(' | '));
} finally {
  await browser.close();
}

if (failures.length) {
  console.log(`\nFAIL: ${failures.join(', ')}`);
  process.exit(1);
}
console.log('\nULTRONE globe smoke QA: all checks passed');
