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

test("旧领域链接保留原中文目的地，切换语言后仍是同一领域", async ({ page }) => {
  await page.goto('/SRD/core-resources/domains/#arcana');
  await expect(page).toHaveURL(/#section-blade$/);
  await expect(page.locator('#section-blade')).toHaveText('利刃');
  await page.locator('#language-button').click();
  await expect(page.locator('#section-blade')).toHaveText('BLADE');
});

test("英文职业链接切到中文后仍定位职业，不落到错位的职业特性", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('dh-srd-lang', 'en'));
  await page.goto('/SRD/core-resources/classes/#druid');
  await expect(page).toHaveURL(/#section-druid$/);
  await expect(page.locator('#section-druid')).toHaveText('DRUID');
  await page.locator('#language-button').click();
  await expect(page.locator('#section-druid')).toHaveText('德鲁伊');
});

test("旧环境位阶链接在目录重组后仍能归一化并切换语言", async ({ page }) => {
  await page.goto('/SRD/adversaries-and-environments/environment-data/#mountain-pass');
  await expect(page).toHaveURL(/#section-tier-4$/);
  await expect(page.locator('#section-tier-4')).toHaveCount(1);
  await page.locator('#language-button').click();
  await expect(page.locator('#section-tier-4')).toHaveCount(1);
  await expect(page.locator('#section-tier-4')).toHaveAttribute('data-anchor', 'section-tier-4');
});

test("敌人小节按资料卡身份对应，旧英文名称链接仍可打开", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('dh-srd-lang', 'en'));
  await page.goto('/SRD/adversaries-and-environments/adversary-data/#acid-burrower');
  await expect(page).toHaveURL(/#section-adversary-acid-burrower$/);
  await expect(page.locator('#section-adversary-acid-burrower')).toContainText('ACID BURROWER');
  await page.locator('#language-button').click();
  await expect(page.locator('#section-adversary-acid-burrower')).toContainText('酸液掘地者');
});
