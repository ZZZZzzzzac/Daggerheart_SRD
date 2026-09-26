import { expect, test } from "@playwright/test";

const term = (page, id, language = "zh") => page.locator(`.srd-language.lang-${language} .term-link[data-term-id="${id}"]`).first();

test("term hints support hover, pointer transfer, keyboard, dismissal, and full rules", async ({ page }) => {
  await page.goto("/SRD/core-mechanics/");
  const trigger = term(page, "stress");
  const popup = page.locator("#term-popover");
  await trigger.hover();
  await expect(popup).toBeVisible();
  await expect(popup.locator(".term-title")).toHaveText("压力点");
  await expect(popup.locator(".term-translation")).toHaveText("Stress");
  await expect(popup.locator(".term-quote")).toContainText("压力点 代表角色所能承受");
  await popup.hover();
  await expect(popup).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(popup).toBeHidden();

  await trigger.focus();
  await expect(popup).toBeVisible();
  await page.keyboard.press("Tab");
  await expect(popup.locator(".term-source")).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(popup.locator(".term-close")).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(trigger).toBeFocused();
  await expect(popup).toBeHidden();

  await trigger.press("Enter");
  await popup.locator(".term-source").click();
  await expect(page).toHaveURL(/core-mechanics\/#attack-rolls$/);
  await expect(page.locator(".lang-zh #attack-rolls")).toHaveText("压力点");
  await expect(popup).toBeHidden();
});

test("mobile hints fit the viewport and persist the off preference", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/SRD/core-mechanics/");
  const trigger = term(page, "stress");
  await trigger.click();
  const popup = page.locator("#term-popover");
  await expect(popup).toBeVisible();
  const rect = await popup.boundingBox();
  expect(rect.x).toBeGreaterThanOrEqual(0);
  expect(rect.x + rect.width).toBeLessThanOrEqual(390);
  expect(rect.y).toBeGreaterThanOrEqual(0);
  expect(rect.y + rect.height).toBeLessThanOrEqual(844);
  await popup.locator(".term-close").click();
  await expect(popup).toBeHidden();

  await page.locator("#menu-button").click();
  await page.locator("#term-toggle").click();
  await expect(page.locator("#term-toggle")).toHaveAttribute("aria-pressed", "false");
  await page.reload();
  await expect(page.locator("#term-toggle")).toHaveAttribute("aria-pressed", "false");
  await trigger.click();
  await expect(page).toHaveURL(/#attack-rolls$/);
  await expect(popup).toBeHidden();
});

test("English terms link to the actual English rule and language switch dismisses hints", async ({ page }) => {
  await page.goto("/SRD/core-mechanics/");
  await term(page, "stress").click();
  await page.locator("#language-button").click();
  await expect(page.locator("#term-popover")).toBeHidden();
  const trigger = term(page, "stress", "en");
  await trigger.click();
  await expect(page.locator("#term-title")).toHaveText("Stress");
  await expect(page.locator("#term-quote")).toContainText("Stress represents how much");
  await page.getByRole("link", { name: "Read the full rule" }).click();
  await expect(page).toHaveURL(/#stress$/);
  await expect(page.locator(".lang-en #stress")).toHaveText("STRESS");
});

test("plain rule links remain available without JavaScript", async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  await page.goto("http://127.0.0.1:8766/SRD/core-mechanics/");
  await term(page, "stress").click();
  await expect(page).toHaveURL(/#attack-rolls$/);
  await expect(page.locator(".lang-zh #attack-rolls")).toHaveText("压力点");
  await context.close();
});

test("tab can leave the popup without trapping keyboard navigation", async ({ page }) => {
  await page.goto("/SRD/core-mechanics/");
  const trigger = term(page, "stress");
  await trigger.focus();
  await page.keyboard.press("Tab");
  await page.keyboard.press("Tab");
  await page.keyboard.press("Tab");
  await expect(trigger).not.toBeFocused();
  await expect(page.locator(".term-close")).not.toBeFocused();
  await expect(page.locator(".term-source")).not.toBeFocused();
});

test("outside click dismisses hints and the theme remains readable", async ({ page }) => {
  await page.goto("/SRD/core-mechanics/");
  await page.locator("#theme-button").click();
  await term(page, "stress").click();
  const popup = page.locator("#term-popover");
  await expect(popup).toBeVisible();
  const colors = await popup.evaluate((item) => ({ color: getComputedStyle(item).color, background: getComputedStyle(item).backgroundColor }));
  expect(colors.color).not.toBe(colors.background);
  await page.locator(".site-header .wordmark-text").click();
  await expect(popup).toBeHidden();
});

test("multiblock verbatim excerpts survive the full Hugo build without corrupting headings", async ({ page }) => {
  await page.goto("/SRD/core-mechanics/");
  await term(page, "damage-thresholds").click();
  await expect(page.locator("#term-popover .term-label")).toHaveText("本站译文 · 原文摘录");
  await expect(page.locator("#term-quote")).toContainText("若伤害被减至 0 或更低，则不标记生命点。");
  const text = await page.locator("#term-quote").textContent();
  expect(text.split("\n\n")).toHaveLength(5);
  expect(text).not.toContain("<p>");
  await expect(page.locator(".lang-zh #attack-rolls")).toHaveCount(1);
  await expect(page.locator(".lang-zh #attack-rolls")).toHaveText("压力点");
});
