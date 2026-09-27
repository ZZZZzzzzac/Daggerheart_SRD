import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { parseGlossary } from "../../static/js/glossary-core.mjs";

const descriptions = new Map(parseGlossary(readFileSync(new URL("../../data/glossary.md", import.meta.url), "utf8")).terms.map(term => [term.zh, term.description]));

const term = (page, id, language = "zh") => page.locator(`.srd-language.lang-${language} .term-link[data-term-zh="${id === "damage-thresholds" ? "伤害阈值" : "压力点"}"]`).first();

test("term hints support hover, pointer transfer, keyboard, dismissal, and full rules", async ({ page }) => {
  await page.goto("/SRD/core-mechanics/");
  const trigger = term(page, "stress");
  const popup = page.locator("#term-popover");
  await trigger.hover();
  await expect(popup).toBeVisible();
  await expect(popup.locator(".term-title")).toHaveText("压力点");
  await expect(popup.locator(".term-translation")).toHaveCount(0);
  await expect(popup.locator(".term-quote")).toHaveText(descriptions.get("压力点"));
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
  await expect(page).toHaveURL(/core-mechanics\/#rule-stress$/);
  await expect(page.locator(".lang-zh #rule-stress")).toHaveText("压力点");
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
  await expect(page).toHaveURL(/#rule-stress$/);
  await expect(popup).toBeHidden();
});

test("English text remains available without glossary matching", async ({ page }) => {
  await page.goto("/SRD/core-mechanics/");
  await page.locator("#language-button").click();
  await expect(page.locator(".lang-en .term-link")).toHaveCount(0);
  await expect(page.locator(".srd-language.lang-en")).toBeVisible();
});

test("plain rule links remain available without JavaScript", async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  await page.goto("http://127.0.0.1:8766/SRD/core-mechanics/");
  await term(page, "stress").click();
  await expect(page).toHaveURL(/#rule-stress$/);
  await expect(page.locator(".lang-zh #rule-stress")).toHaveText("压力点");
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
  await expect(page.locator("#term-popover .term-label")).toHaveCount(0);
  await expect(page.locator("#term-quote")).toContainText("若伤害被减至 0 或更低，则不标记生命点。");
  const text = await page.locator("#term-quote").textContent();
  expect(text).toBe(descriptions.get("伤害阈值"));
  expect(text).not.toContain("<p>");
  await expect(page.locator(".lang-zh #rule-stress")).toHaveCount(1);
  await expect(page.locator(".lang-zh #rule-stress")).toHaveText("压力点");
});

test("terms without an explanation or jump link still show their names", async ({ page }) => {
  // Keep the empty-term case independent of the user's completed glossary.
  await page.route("**/SRD/core-mechanics/", async route => {
    const response = await route.fetch();
    const original = await response.text();
    const body = original.replace(/<a\b[^>]*data-term-zh="游戏主持人"[^>]*>[\s\S]*?<\/a>/,
      '<span class="term-link" data-term-id="empty-fixture" data-term-zh="游戏主持人" data-term-quote="">游戏主持人</span>');
    expect(body).not.toBe(original);
    await route.fulfill({ response, body });
  });
  await page.goto("/SRD/core-mechanics/");
  const trigger = page.locator('.lang-zh span.term-link[data-term-zh="游戏主持人"]').first();
  await trigger.focus();
  await trigger.press("Enter");
  await expect(page.locator("#term-title")).toHaveText("游戏主持人");
  await expect(page.locator("#term-popover .term-translation")).toHaveCount(0);
  await expect(page.locator("#term-quote")).toBeHidden();
  await expect(page.locator("#term-popover .term-source")).toBeHidden();
  await trigger.press("Tab");
  await expect(page.locator("#term-popover .term-close")).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(trigger).toBeFocused();
});
