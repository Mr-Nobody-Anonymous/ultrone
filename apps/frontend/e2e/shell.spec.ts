// Copyright (c) Ultrone Contributors. All rights reserved.
/**
 * Cockpit shell + navigation E2E (brief items #2, #3, #31).
 * Validates the three-panel shell, the persistent environment boundary,
 * global status dock, and universal search / command palette wiring.
 */
import { test, expect } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.goto('/');
  await expect(page.getByTestId('dock-alerts-link')).toBeVisible({ timeout: 15000 });
});

test('dashboard loads with three-panel cockpit shell', async ({ page }) => {
  await expect(page.getByText('SIMULATION MODE • NO PHYSICAL ACTUATION')).toBeVisible();
  await expect(page.getByText('Overview')).toBeVisible();
});

test('environment mode banner is persistent and unmistakable', async ({ page }) => {
  // The simulation boundary must be visible on every page, not hidden in settings.
  for (const route of ['/simulation', '/devices', '/mcp', '/evaluation', '/system/health']) {
    await page.goto(route);
    await expect(page.getByText('SIMULATION MODE • NO PHYSICAL ACTUATION')).toBeVisible();
  }
});

test('global dock shows live chain and policy status', async ({ page }) => {
  await expect(page.getByText('CHAIN: ✓ VALID')).toBeVisible();
  await expect(page.getByText('POLICY: NORMAL')).toBeVisible();
  await expect(page.getByText('EVENTS: 18421')).toBeVisible();
});

test('command palette opens with Ctrl+K and executes search', async ({ page }) => {
  await page.keyboard.press('Control+KeyK');
  await expect(page.getByPlaceholder(/search/i)).toBeVisible();
  await page.keyboard.type('device-17');
  await expect(page.getByText('device-17').first()).toBeVisible();
});

test('escape closes command palette', async ({ page }) => {
  await page.keyboard.press('Control+KeyK');
  await expect(page.getByPlaceholder(/search/i)).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByPlaceholder(/search/i)).toBeHidden();
});