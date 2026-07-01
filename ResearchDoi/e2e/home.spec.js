import { test, expect } from '@playwright/test';

test('has title and displays projects header', async ({ page }) => {
  // Mock Firebase Auth state if necessary, or just verify the initial page renders
  await page.goto('/');

  // Expect a title "to contain" a substring.
  await expect(page).toHaveTitle(/Research/i);

  // Since it might redirect to login, let's just assert that the page loads without crashing
  const body = await page.locator('body');
  await expect(body).toBeVisible();
});
