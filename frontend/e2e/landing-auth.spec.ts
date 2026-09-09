import { test, expect } from "@playwright/test";

test("landing intro: VERITY overlay plays once on first visit", async ({ page }) => {
  await page.goto("/");
  // The intro overlay appears on the first (flag-less) visit.
  const overlay = page.getByTestId("intro-overlay");
  await expect(overlay).toBeVisible({ timeout: 6000 });

  // The full cinematic intro (write → hold → zoom through the I-dot) completes
  // in ~3.5s and the landing page settles.
  await expect(overlay).toBeHidden({ timeout: 6000 });
  await expect(page.getByRole("heading", { name: /Intelligence that explains/i })).toBeVisible();
});

test("landing intro: respects reduced motion", async ({ browser }) => {
  const context = await browser.newContext({ reducedMotion: "reduce" });
  const page = await context.newPage();
  await page.goto("/");
  // Reduced motion skips the zoom and cuts straight through; the page is usable.
  await expect(page.getByTestId("intro-overlay")).toBeHidden({ timeout: 2500 });
  await expect(page.getByRole("heading", { name: /Intelligence that explains/i })).toBeVisible();
  await context.close();
});

test("landing intro: does not replay on internal section navigation", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("intro-overlay")).toBeHidden({ timeout: 6000 });
  // Trigger a section click; verify the URL hash updates and no overlay returns.
  await page.getByRole("navigation", { name: "Landing sections" }).getByRole("link", { name: "How it works" }).click();
  await expect(page).toHaveURL(/#how-it-works/);
  await expect(page.getByTestId("intro-overlay")).toHaveCount(0);
});

test("auth journey: login -> signup -> forgot/reset", async ({ page }) => {
  // Login page provides account-creation and password-reset links.
  await page.goto("/login");
  await expect(page.getByRole("link", { name: "Create an account" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Forgot password?" })).toBeVisible();

  // Signup flow creates a viewer account and signs in.
  const username = `e2e_${Date.now()}`;
  await page.getByRole("link", { name: "Create an account" }).click();
  await expect(page).toHaveURL(/\/signup/);
  await page.getByLabel(/Full name/).fill("E2E Viewer");
  await page.getByLabel(/Work email/).fill(`${username}@example.org`);
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password", { exact: true }).fill("E2EPassw0rd!");
  await page.getByLabel(/Confirm password/).fill("E2EPassw0rd!");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/dashboard/);
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();

  // Sign out, then run the password-reset flow for the new account.
  await page.getByLabel("Account menu").click();
  await page.getByRole("menuitem", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login/);

  await page.getByRole("link", { name: "Forgot password?" }).click();
  await expect(page).toHaveURL(/\/forgot-password/);
  await page.getByLabel(/Username or email/).fill(username);
  await page.getByRole("button", { name: "Send reset instructions" }).click();
  await expect(page.getByText(/If an account exists/i)).toBeVisible();

  // Development build exposes a demo reset link that walks to the reset page.
  await page.getByRole("link", { name: /Open reset page/i }).click();
  await expect(page).toHaveURL(/\/reset-password/);
  await page.getByLabel(/New password/).fill("FreshE2E!Passw0rd");
  await page.getByLabel(/Confirm new password/).fill("FreshE2E!Passw0rd");
  await page.getByRole("button", { name: "Set new password" }).click();
  await expect(page.getByText(/Your password has been reset/i)).toBeVisible();

  // New password works.
  await page.getByRole("link", { name: "Go to sign in" }).click();
  await expect(page).toHaveURL(/\/login/);
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password", { exact: true }).fill("FreshE2E!Passw0rd");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/dashboard/);
});
