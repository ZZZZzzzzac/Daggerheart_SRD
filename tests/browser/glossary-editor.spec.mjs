import { readFileSync } from "node:fs";
import { expect, test } from "@playwright/test";
import { parseGlossary } from "../../static/js/glossary-core.mjs";

const initialTerms = parseGlossary(readFileSync(new URL("../../data/glossary.md", import.meta.url), "utf8")).terms;
const removableName = initialTerms.find(term => initialTerms.filter(item => item.zh === term.zh).length === 1).zh;

test.use({ httpCredentials: { username: "admin", password: "playwright" } });

async function openEditor(page) {
  await page.goto("/SRD/edit/?path=glossary");
  await expect(page.locator("#glossary-count")).toHaveText(`${initialTerms.length} 条术语`);
}

test("editor can add, update and delete terms, and batch publish the Markdown document", async ({ page }) => {
  let changes;
  await page.route("**/SRD/api/save", async (route) => {
    changes = route.request().postDataJSON();
    await route.fulfill({ json: { versions: Object.fromEntries(changes.changes.map((item) => [item.path, "test-next"])), gitSync: { status: "synced" } } });
  });
  await openEditor(page);
  await page.getByRole("button", { name: "新增术语", exact: true }).click();
  await page.locator("#glossary-zh").fill("浏览器测试术语");
  await expect(page.locator("#pending-count")).toHaveText("待发布 1 项");
  await page.getByRole("button", { name: "编辑 Markdown", exact: true }).click();
  expect(await page.locator("#editor-textarea").inputValue()).toContain("## 中文名：浏览器测试术语");
  await page.locator("#glossary-form").click();
  await expect(page.locator("#glossary-zh")).toHaveValue("浏览器测试术语");
  // Switching to an ordinary document and back preserves the glossary draft.
  await page.locator("#contents-tree .tree-page-link").filter({ hasText: /^介绍$/ }).click();
  await expect(page.locator("#glossary-editor")).toBeHidden();
  await page.locator("#editor-textarea").fill((await page.locator("#editor-textarea").inputValue()) + "\n\n编辑器批量测试。\n");
  await page.locator("#contents-tree .tree-page-link").filter({ hasText: "术语表" }).click();
  await expect(page.locator("#glossary-zh")).toHaveValue("浏览器测试术语");
  await expect(page.locator("#pending-count")).toHaveText("待发布 2 项");
  // Use an existing unique name: the user may freely remove or rename entries.
  await page.locator("#glossary-search").fill(removableName);
  await page.locator("#glossary-list button").first().click();
  await page.getByRole("button", { name: "删除术语", exact: true }).click();
  await page.getByRole("button", { name: "确认删除这条术语", exact: true }).click();
  await page.locator("#save-btn").click();
  await page.locator("#publish-name").fill("浏览器测试");
  await page.getByRole("button", { name: "确认发布", exact: true }).click();
  await expect(page.locator("#save-status")).toHaveText("已同步至 GitHub");
  const glossaryChange = changes.changes.find((item) => item.path === "data/glossary.md");
  expect(glossaryChange.baseVersion).toBeTruthy();
  const parsed = parseGlossary(glossaryChange.content);
  expect(parsed.terms.some((term) => term.zh === "浏览器测试术语")).toBe(true);
  expect(parsed.terms.some((term) => term.zh === removableName)).toBe(false);
  expect(changes.changes.some((item) => item.path === "src/pages/introduction/zh.md")).toBe(true);
});

test("invalid Markdown and conflicting publications preserve local work", async ({ page }) => {
  await page.route("**/SRD/api/save", (route) => route.fulfill({ status: 409, json: { error: "版本冲突", conflicts: [{ path: "data/glossary.md", currentContent: "# 服务器术语表\n", currentVersion: "newer" }] } }));
  await openEditor(page);
  await page.getByRole("button", { name: "编辑 Markdown", exact: true }).click();
  await expect(page.locator("#editor-textarea")).toBeVisible();
  await page.locator("#editor-textarea").fill("# 本地术语表\n\n## 无效标题\n");
  await page.locator("#glossary-form").click();
  await expect(page.locator("#glossary-error")).toContainText("Markdown 格式错误");
  await expect(page.locator("#glossary-new")).toBeDisabled();
  await page.getByRole("button", { name: "编辑 Markdown", exact: true }).click();
  await page.locator("#editor-textarea").fill("# 本地术语表\n");
  await page.locator("#save-btn").click();
  await page.locator("#publish-name").fill("冲突测试");
  await page.getByRole("button", { name: "确认发布", exact: true }).click();
  await expect(page.locator("#publish-error")).toContainText("版本冲突");
  expect(await page.locator("#editor-textarea").inputValue()).toBe("# 本地术语表\n");
  await page.locator("#publish-cancel").click();
  await page.locator("#accept-server").click();
  await expect(page.locator("#editor-textarea")).toHaveValue("# 服务器术语表\n");
  await expect(page.locator("#pending-count")).toHaveText("待发布 0 项");
});

test("glossary form works at phone width", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openEditor(page);
  await page.getByRole("button", { name: "新增术语", exact: true }).click();
  await page.locator("#glossary-zh").fill("手机测试");
  await expect(page.locator("#glossary-zh")).toHaveValue("手机测试");
  const fits = await page.locator("#glossary-editor").evaluate((item) => item.getBoundingClientRect().right <= innerWidth + 1);
  expect(fits).toBe(true);
});

test("manual Markdown editing preserves the complete large terminology document", async ({ page }) => {
  await openEditor(page);
  await page.getByRole("button", { name: "编辑 Markdown", exact: true }).click();
  const markdown = page.locator("#editor-textarea");
  await markdown.press("Control+End");
  await page.keyboard.insertText("\n手工维护测试文本。\n");
  const parsed = parseGlossary(await markdown.inputValue());
  expect(parsed.terms).toHaveLength(initialTerms.length);
  expect(parsed.terms.at(-1).description).toBe("手工维护测试文本。");
  await page.locator("#glossary-form").click();
  await expect(page.locator("#glossary-count")).toHaveText(`${initialTerms.length} 条术语`);
  await expect(page.locator("#pending-count")).toHaveText("待发布 1 项");
});
