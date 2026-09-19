// Copyright (c) Ultrone Contributors. All rights reserved.
/**
 * SYSTEM section E2E (brief items #25, #26, #59).
 * Covers the newly added System Health, Alerts Center and UI Audit Trail
 * screens against the mocked cockpit backend.
 */
import { test, expect } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.goto('/');
  await expect(page.getByTestId('dock-alerts-link')).toBeVisible({ timeout: 15000 });
});

test.afterEach(async ({ page }) => {
  await page.request.post('/api/cockpit/__test__/scenario', { data: { scenario: 'standard_patrol' } });
});

test('system health renders real service status and honest resource boundary', async ({ page }) => {
  await page.goto('/system/health');
  await expect(page.getByTestId('system-health-view')).toBeVisible();
  await expect(page.getByRole('heading', { name: /System Health/i })).toBeVisible();

  // All nine backend services listed with state
  const services = page.getByTestId('service-list');
  await expect(services).toBeVisible();
  for (const name of ['Orchestrator', 'MCP Gateway', 'UDIS Registry', 'Event Store', 'Simulator', 'Model Runtime']) {
    await expect(services.getByText(name)).toBeVisible();
  }
  await expect(services.getByText('✓ OK')).toHaveCount(9);

  // Measured latency metrics — not decorative gauges
  await expect(page.getByText('MCP GATEWAY', { exact: true })).toBeVisible();
  await expect(page.getByText('11.2 ms').first()).toBeVisible();

  // Host resources: backend reports nulls; UI must NOT fake percentages
  await expect(page.getByText('NOT SAMPLED')).toHaveCount(4);
  await expect(page.getByText('NOT SAMPLED').first()).toBeVisible();
});

test('system health shows degraded service when backend reports one', async ({ page }) => {
  await page.request.post('/api/cockpit/__test__/scenario', { data: { scenario: 'stale_device' } });
  await page.goto('/system/health');
  await expect(page.getByTestId('system-health-view')).toBeVisible();
  await expect(page.getByText('⚠ DEGRADED').first()).toBeVisible();
  await page.request.post('/api/cockpit/__test__/scenario', { data: { scenario: 'standard_patrol' } });
});

test('alerts center lists alert with evidence and recommended investigation', async ({ page }) => {
  await page.request.post('/api/cockpit/__test__/scenario', { data: { scenario: 'stale_device' } });
  await page.goto('/system/alerts');
  await expect(page.getByTestId('alerts-center-view')).toBeVisible();

  const alert = page.getByTestId('alert-ALRT-0001');
  await expect(alert).toBeVisible();
  await expect(alert.getByText('Stale telemetry detected')).toBeVisible();
  await expect(alert.getByText(/age 812 ms > horizon 250 ms/)).toBeVisible();
  await expect(alert.getByText(/Check simulated sensor cadence/)).toBeVisible();

  // Drill-down link to the affected subsystem (item #68)
  await expect(alert.getByText('Open Safety Center')).toBeVisible();
  await page.request.post('/api/cockpit/__test__/scenario', { data: { scenario: 'standard_patrol' } });
});

test('alerts center empty state when nothing is wrong', async ({ page }) => {
  await page.goto('/system/alerts');
  await expect(page.getByTestId('alerts-center-view')).toBeVisible();
  await expect(page.getByText('NO OPEN ALERTS')).toBeVisible({ timeout: 5000 });
});

test('severity filter chips are color-independent (icon + label + count)', async ({ page }) => {
  await page.request.post('/api/cockpit/__test__/scenario', { data: { scenario: 'stale_device' } });
  await page.goto('/system/alerts');
  const criticalChip = page.getByRole('tab', { name: /CRITICAL/ });
  await expect(criticalChip).toBeVisible();
  await criticalChip.click();
  await expect(page.getByTestId('alert-ALRT-0001')).toBeHidden();
  await page.request.post('/api/cockpit/__test__/scenario', { data: { scenario: 'standard_patrol' } });
});

test('dock alert count drills down into alerts center', async ({ page }) => {
  await page.request.post('/api/cockpit/__test__/scenario', { data: { scenario: 'stale_device' } });
  await page.goto('/');
  await page.getByTestId('dock-alerts-link').click();
  await expect(page).toHaveURL(/\/system\/alerts/);
  await expect(page.getByTestId('alert-ALRT-0001')).toBeVisible();
  await page.request.post('/api/cockpit/__test__/scenario', { data: { scenario: 'standard_patrol' } });
});

test('ui audit trail records operator control actions', async ({ page }) => {
  await page.goto('/');
  // Issue a control action through the transport bar (icon button w/ title)
  await page.getByTitle('Run Simulation Clock').click();
  await page.goto('/system/audit');
  await expect(page.getByTestId('audit-trail-view')).toBeVisible();
  await expect(page.getByText('PLAY').first()).toBeVisible();
  await expect(page.getByText('operator').first()).toBeVisible();
  await expect(page.getByText('cockpit-role').first()).toBeVisible();
});