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
  await page.goto("/SRD/core-mechanics/equipment/");

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
  await page.goto("/SRD/core-mechanics/equipment/");

  const lineCount = async (locator) => locator.evaluate((element) => {
    const range = document.createRange();
    range.selectNodeContents(element);
    return new Set(
      [...range.getClientRects()].filter((rect) => rect.width > 0).map((rect) => Math.round(rect.top)),
    ).size;
  });

  const row = page.locator("tr", { hasText: "传奇阔剑" }).first();
  expect(await lineCount(page.locator("th", { hasText: "属性" }).first())).toBe(1);
  expect(await lineCount(page.locator("th", { hasText: "负荷" }).first())).toBe(1);
  for (let column = 0; column < 5; column += 1) {
    expect(await lineCount(row.locator("td").nth(column))).toBe(1);
  }

  const armorRow = page.locator("tr", { hasText: "传奇填充布甲" }).first();
  const thresholdCell = armorRow.locator("td").nth(1);
  expect(await lineCount(thresholdCell)).toBe(1);
  expect((await thresholdCell.boundingBox()).width).toBeGreaterThanOrEqual(99);

  const tableMetrics = await page.locator(".article-body .srd-language.lang-zh table").evaluateAll((tables) => tables.map((table) => ({
    columnCount: table.tHead.rows[0].cells.length,
    widths: [...table.tHead.rows[0].cells].map((cell) => Math.round(cell.getBoundingClientRect().width)),
    dataLineCounts: [...table.tBodies[0].rows].flatMap((tableRow) => [...tableRow.cells].map((cell, column) => {
      const range = document.createRange();
      range.selectNodeContents(cell);
      return {
        column,
        lines: new Set([...range.getClientRects()].filter((rect) => rect.width > 0).map((rect) => Math.round(rect.top))).size,
      };
    })),
  })));
  for (const columnCount of [6, 4]) {
    const sameKind = tableMetrics.filter((table) => table.columnCount === columnCount);
    const expectedWidths = sameKind[0].widths;
    sameKind.forEach((table) => expect(table.widths).toEqual(expectedWidths));
    const nowrapColumns = columnCount === 6 ? new Set([1, 2, 3, 4]) : new Set([1, 2]);
    sameKind.forEach((table) => {
      table.dataLineCounts.filter(({ column }) => nowrapColumns.has(column)).forEach(({ lines }) => expect(lines).toBe(1));
    });
  }

  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  const fitsMobileViewport = await page.locator(".table-scroll").first().evaluate(
    (wrapper) => wrapper.scrollWidth <= wrapper.clientWidth + 1,
  );
  expect(fitsMobileViewport).toBe(true);
});
