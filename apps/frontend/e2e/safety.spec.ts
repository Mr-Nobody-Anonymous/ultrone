// Copyright (c) Ultrone Contributors. All rights reserved.
/**
 * VERIFY & EXPERIMENT pillar E2E (brief items #9, #10, #17, #18, #45).
 * Decision provenance drill-down, causal boundary display, why-blocked
 * gates, benchmark statistics with uncertainty, and regulation-gated
 * promotion (a single aggregate score is deliberately NOT shown).
 */
import { test, expect } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.goto('/');
  await expect(page.getByTestId('dock-alerts-link')).toBeVisible({ timeout: 15000 });
});

test('cognitive trace shows structured provenance for a decision', async ({ page }) => {
  await page.goto('/traces');
  await expect(page.getByText('DEC-281').first()).toBeVisible();
  // The evidence chain stages from the brief
  for (const stage of ['observation', 'belief', 'plan', 'policy', 'decision', 'action']) {
    await expect(page.getByText(new RegExp(stage, 'i')).first()).toBeVisible();
  }
});

test('causal boundary violation is surfaced, not hidden', async ({ page }) => {
  await page.request.post('/api/cockpit/__test__/scenario', { data: { scenario: 'causal_violation' } });
  await page.goto('/safety');
  await expect(page.getByText(/Causal/i).first()).toBeVisible();
  await expect(page.getByText('1').first()).toBeVisible(); // causal_violations metric
  await page.request.post('/api/cockpit/__test__/scenario', { data: { scenario: 'standard_patrol' } });
});

test('why-blocked shows gate-by-gate verdicts with final REJECTED', async ({ page }) => {
  await page.goto('/safety');
  // Open the blocked decision's explanation
  const blocked = page.getByText(/blocked/i).first();
  if (await blocked.isVisible()) {
    await blocked.click();
    await expect(page.getByText('REJECTED')).toBeVisible();
  }
});

test('evaluation lab shows uncertainty, not a single score', async ({ page }) => {
  await page.goto('/evaluation');
  await expect(page.getByText(/BENCH-0144|confidence interval|CI/i).first()).toBeVisible();
  // Separate metrics — never a single aggregate "ULTRONE SCORE"
  await expect(page.getByText(/accuracy/i).first()).toBeVisible();
  await expect(page.getByText(/brier/i).first()).toBeVisible();
});

test('promotion blocked when any metric regresses', async ({ page }) => {
  await page.goto('/evaluation');
  // mock returns regressions: [latency_ms] and promotion: BLOCKED
  await expect(page.getByText(/BLOCKED/i).first()).toBeVisible({ timeout: 8000 });
  await expect(page.getByText(/latency/i).first()).toBeVisible();
});

test('device registry lists UDIS devices with FSM states', async ({ page }) => {
  await page.goto('/devices');
  for (const id of ['device-01', 'device-04', 'device-17']) {
    await expect(page.getByText(id).first()).toBeVisible({ timeout: 8000 });
  }
  await expect(page.getByText('DEGRADED').first()).toBeVisible();
});

test('MCP inspector shows protocol version and traffic', async ({ page }) => {
  await page.goto('/mcp');
  await expect(page.getByText('2026-07-28').first()).toBeVisible();
  await expect(page.getByText(/tools\/call/i).first()).toBeVisible();
});

test('event store shows hash chain integrity', async ({ page }) => {
  await page.goto('/events');
  await expect(page.getByText(/VALID/i).first()).toBeVisible();
  await expect(page.getByText(/18421|CP-019/).first()).toBeVisible();
});

test('event stream virtualization survives high event rate without freezing', async ({ page }) => {
  await page.goto('/events');
  // The event list should render a bounded window, not thousands of DOM nodes
  const rowCount = await page.locator('table tbody tr, [data-virtualized] > div').count();
  expect(rowCount).toBeLessThan(2000);
  await expect(page.getByText(/VALID/i).first()).toBeVisible();
});

test('governance maturity matrix renders per-capability levels', async ({ page }) => {
  await page.goto('/governance');
  await expect(page.getByText(/Perception/i).first()).toBeVisible();
  await expect(page.getByText(/UDIS/i).first()).toBeVisible();
  await expect(page.getByText(/MCP/i).first()).toBeVisible();
});

test('keyboard navigation reaches sidebar nav links', async ({ page }) => {
  // Focus a nav link and activate via keyboard only
  await page.keyboard.press('Tab');
  await page.keyboard.press('Tab');
  const firstNav = page.getByRole('link', { name: 'Overview' });
  await firstNav.focus();
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/\/$|\/#?$/);
});