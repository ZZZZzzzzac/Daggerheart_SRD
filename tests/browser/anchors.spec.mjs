import { expect, test } from "@playwright/test";

test("legacy Chinese stress link resolves to thresholds and survives language switching", async ({ page }) => {
  await page.goto("/SRD/core-mechanics/#stress");
  await expect(page).toHaveURL(/#rule-hit-points-damage-thresholds$/);
  await expect(page.locator("#rule-hit-points-damage-thresholds")).toHaveText("生命点与伤害阈值");
  await page.locator("#language-button").click();
  await expect(page.locator("#rule-hit-points-damage-thresholds")).toHaveText("HIT POINTS & DAMAGE THRESHOLDS");
});

test("legacy English stress retains its own meaning, canonical stress works in Chinese", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("dh-srd-lang", "en"));
  await page.goto("/SRD/core-mechanics/#stress");
  await expect(page).toHaveURL(/#rule-stress$/);
  await expect(page.locator("#rule-stress")).toHaveText("STRESS");
  await page.locator("#language-button").click();
  await expect(page.locator("#rule-stress")).toHaveText("压力点");
});

test("legacy experience link resolves correctly and new English headings share its target", async ({ page }) => {
  await page.goto("/SRD/character-creation/#step-6-create-your-background");
  await expect(page).toHaveURL(/#rule-step-7-create-your-experiences$/);
  await expect(page.locator("#rule-step-7-create-your-experiences")).toContainText("经历");
  await page.locator("#language-button").click();
  await expect(page.locator("#rule-step-7-create-your-experiences")).toContainText("Experiences");
});
