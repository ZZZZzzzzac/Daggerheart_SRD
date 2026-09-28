import { expect, test } from "@playwright/test";


test("contents, search, language, and theme work in a real browser", async ({ page }) => {
  await page.goto("/SRD/core-mechanics/");
  await expect(page.locator(".tree-page.current")).toHaveAttribute("open", "");

  const firstHeading = page.locator(".tree-page.current .tree-headings .level-2 a").first();
  const anchor = await firstHeading.getAttribute("data-anchor");
  await firstHeading.click();
  await expect(page).toHaveURL(new RegExp(`#${anchor}$`));
  await expect(page.locator(`.lang-zh #${anchor}`)).toBeVisible();
  await expect(firstHeading).toHaveClass(/active/);

  await page.locator("#search-button").click();
  await page.locator("#search-input").fill("动作掷骰");
  await expect(page.locator("#search-results .search-result").first()).toBeVisible();
  const searchResult = page.locator("#search-results .search-result a").first();
  const resultHref = await searchResult.getAttribute("href");
  expect(resultHref).toMatch(/#[a-z0-9-]+$/);
  await searchResult.click();
  await expect(page).toHaveURL(new RegExp(resultHref.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "$"));
  await expect(page.locator("#search-dialog")).not.toHaveAttribute("open", "");

  await page.locator("#language-button").click();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(page.locator(".srd-language.lang-en")).toBeVisible();
  await expect(page.locator(".srd-language.lang-zh")).toBeHidden();

  const originalTheme = await page.locator("html").getAttribute("data-theme");
  await page.locator("#theme-button").click();
  await expect(page.locator("html")).not.toHaveAttribute("data-theme", originalTheme);
});


test("mobile contents drawer opens and closes", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/SRD/introduction/");

  await page.locator("#menu-button").click();
  await expect(page.locator("body")).toHaveClass(/sidebar-open/);
  await expect(page.locator("#site-sidebar")).toBeVisible();

  await page.locator("#sidebar-backdrop").click({ position: { x: 380, y: 400 } });
  await expect(page.locator("body")).not.toHaveClass(/sidebar-open/);
});


test("equipment table renders adjacent bold spans and Chinese punctuation", async ({ page }) => {
  await page.goto("/SRD/core-mechanics/equipment/primary-weapons/");

  const swift = page.locator("td", { hasText: "迅捷：标记 1 压力点" }).first();
  await expect(swift).not.toContainText("**");
  await expect(swift.locator("strong")).toHaveCount(2);

  const cumbersome = page.locator("td", { hasText: "繁琐：灵巧" }).first();
  await expect(cumbersome).not.toContainText("**");
  await expect(cumbersome.locator("strong").first()).toHaveText("繁琐：");

  const brutal = page.locator("td", { hasText: "残暴：伤害骰" }).first();
  await expect(brutal).not.toContainText("**");
  await expect(brutal.locator("strong").first()).toHaveText("残暴：");
});


test("equipment table keeps short leading-column values on one line", async ({ page }) => {
  await page.goto("/SRD/core-mechanics/equipment/primary-weapons/");

  const lineCount = async (locator) => locator.evaluate((element) => {
    const range = document.createRange();
    range.selectNodeContents(element);
    return new Set(
      [...range.getClientRects()].filter((rect) => rect.width > 0).map((rect) => Math.round(rect.top)),
    ).size;
  });

  const row = page.locator("tr", { hasText: "传奇阔剑" }).first();
  expect(await lineCount(page.locator('th[data-column="trait"] .equipment-sort-button > span').first())).toBe(1);
  expect(await lineCount(page.locator('th[data-column="burden"] .equipment-sort-button > span').first())).toBe(1);
  for (const column of ['tier','type','trait','range','damage','burden']) {
    expect(await lineCount(row.locator(`td[data-column="${column}"]`))).toBe(1);
  }

  await page.goto("/SRD/core-mechanics/equipment/armor/");
  const armorRow = page.locator("tr", { hasText: "传奇填充布甲" }).first();
  const thresholdCell = armorRow.locator('td[data-column="thresholds"]');
  expect(await lineCount(thresholdCell)).toBe(1);

  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(await page.locator('.equipment-scroll').first().evaluate(el => el.scrollWidth > el.clientWidth)).toBe(true);
});
