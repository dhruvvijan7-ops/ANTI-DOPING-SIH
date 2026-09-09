import { test, expect, type Page } from "@playwright/test";

// Seeded record ids (backend dev seed / probes).
const ALERT_ID = "69a2690a-0bfc-4cfa-a72f-51d9fa572cb2";
const CASE_REF = "CASE-C14B1A9593";

// The investigator role carries the broadest read journey across the required
// screens (intelligence, alerts, athletes, investigations, reports, audit).
const USERNAME = "investigator";
const PASSWORD = "investigator-Passw0rd!";

async function signIn(page: Page) {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Intelligence that explains/i })).toBeVisible();
  await page.getByRole("link", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/login/);
  await page.getByLabel("Username").fill(USERNAME);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/dashboard/);
}

test("critical journey: landing → login → dashboard → alerts → why flagged → workspace → AI → audit", async ({ page }) => {
  // Landing (13-section marketing page) renders before authentication.
  await signIn(page);

  // Dashboard
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();

  // Sidebar reflects investigator permissions (no Users entry).
  for (const label of ["Intelligence", "Alerts", "Athletes", "Investigations", "Reports", "AI Assistant", "Audit log"]) {
    await expect(page.getByRole("link", { name: label, exact: true })).toBeVisible();
  }
  await expect(page.getByRole("link", { name: "Access & users", exact: true })).toHaveCount(0);

  // Intelligence
  await page.getByRole("link", { name: "Intelligence", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Intelligence" })).toBeVisible();

  // Alerts queue
  await page.getByRole("link", { name: "Alerts", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Alert queue" })).toBeVisible();

  // Why Flagged breakdown on the converted seeded alert
  await page.goto(`/alerts/${ALERT_ID}`);
  await expect(page.getByText(/Why this was flagged/i)).toBeVisible();
  await expect(page.getByText(/potential concern/i)).toBeVisible();
  await expect(page.getByRole("link", { name: /Open linked case/i })).toBeVisible();

  // Follow the linked case into the investigation workspace
  await page.getByRole("link", { name: /Open linked case/i }).click();
  await expect(page.getByText(CASE_REF, { exact: true }).first()).toBeVisible();

  // Evidence tab lists the case file
  await page.getByRole("tab", { name: "Evidence" }).click();
  await expect(page.getByText("Add evidence")).toBeVisible();

  // Grounded AI assistant
  await page.getByRole("tab", { name: "AI assistant" }).click();
  await expect(page.getByText(/Grounded intelligence assistant/i)).toBeVisible();
  await expect(page.getByText(/deterministically from case records/i)).toBeVisible();

  // Reports tab
  await page.getByRole("tab", { name: "Reports" }).click();
  await expect(page.getByText("New report")).toBeVisible();

  // Audit tab preserves the record
  await page.getByRole("tab", { name: "Audit" }).click();
  await expect(page.getByText("Audit trail")).toBeVisible();

  // Sign out via the account menu
  await page.getByLabel("Account menu").click();
  await page.getByRole("menuitem", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login/);
});