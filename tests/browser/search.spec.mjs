import { expect, test } from '@playwright/test';

test('英文命中展示中文小节、原文标记和中文链接，双语结果不重复', async ({ page }) => {
  await page.goto('/SRD/');
  await page.locator('#search-button').click();
  await page.locator('#search-input').fill('Stress');
  const result = page.locator('#search-results a[href="/SRD/core-mechanics/#rule-stress"]');
  await expect(result).toHaveCount(1);
  await expect(result.locator('h3')).toHaveText('压力点');
  await expect(result.locator('.search-result-origin')).toHaveText('匹配原文');
  await expect(result.locator('.search-result-source')).toHaveText('原文：STRESS');
  await page.screenshot({path:'test-results/bilingual-search-desktop.png'});
  await page.setViewportSize({width:390,height:844});
  expect(await page.locator('#search-dialog').evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true);
  await page.screenshot({path:'test-results/bilingual-search-mobile.png'});
  await result.click();
  await expect(page.locator('html')).toHaveAttribute('lang', 'zh-CN');
  await expect(page.locator('#rule-stress')).toHaveText('压力点');
});

test('正文原文互搜、反向互搜和显示语言切换', async ({ page }) => {
  const records = [
    {language:'zh',path:'core-mechanics',anchor:'rule-stress',pageTitle:'核心机制',heading:'压力点',body:'记录角色承受的压力。'},
    {language:'en',path:'core-mechanics',anchor:'rule-stress',pageTitle:'Core Mechanics',heading:'Stress',body:'A uniquely exhausted hero.'},
  ];
  await page.route('**/generated/search-index.json', route => route.fulfill({json:{records}}));
  await page.goto('/SRD/');
  await page.locator('#search-button').click();
  await page.locator('#search-input').fill('exhausted');
  await expect(page.locator('#search-results h3')).toHaveText('压力点');
  await expect(page.locator('#search-results')).toContainText('记录角色承受的压力。');
  await page.locator('#search-input').fill('压力点');
  await expect(page.locator('.search-result-origin')).toHaveCount(0);
  await page.locator('#search-language').click();
  await expect(page.locator('#search-results h3')).toHaveText('Stress');
  await expect(page.locator('.search-result-origin')).toHaveText('Matched Chinese translation');
  await page.locator('#search-results a').click();
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
  await expect(page.locator('#rule-stress')).toHaveText('STRESS');
});

test('索引延迟加载时连续输入、清空只显示最新查询，并且只下载一次', async ({ page }) => {
  let release;
  const gate = new Promise(resolve => { release = resolve; });
  let requested;
  const started = new Promise(resolve => { requested = resolve; });
  let count = 0;
  await page.route('**/generated/search-index.json', async route => {
    count++;
    requested();
    await gate;
    await route.continue();
  });
  await page.goto('/SRD/');
  await page.locator('#search-button').click();
  await page.locator('#search-input').fill('Stress');
  await started;
  await page.locator('#search-input').fill('Druid');
  await page.locator('#search-input').fill('');
  release();
  await expect(page.locator('#search-results li')).toHaveCount(0);
  await expect(page.locator('#search-hint')).toHaveText('输入文字后开始搜索');
  await page.locator('#search-input').fill('Druid');
  await expect(page.locator('#search-results h3').first()).toHaveText('德鲁伊');
  expect(count).toBe(1);
  await page.locator('#search-input').fill('zzzz-no-such-rule');
  await expect(page.locator('#search-hint')).toContainText('中英文均未找到');
});

test('无对应译文的小节明确标注章节回退，手机布局不溢出', async ({ page }) => {
  await page.setViewportSize({width:390,height:844});
  await page.route('**/generated/search-index.json', route => route.fulfill({json:{records:[
    {language:'zh',path:'core-resources/classes',anchor:'section-druid',pageTitle:'职业',heading:'德鲁伊',body:'正文'},
    {language:'en',path:'core-resources/classes',anchor:'english-only',pageTitle:'Classes',heading:'Exclusive',body:'English only'},
  ]}}));
  await page.goto('/SRD/');
  await page.locator('#search-button').click();
  await page.locator('#search-input').fill('Exclusive');
  await expect(page.locator('#search-results h3')).toHaveText('职业');
  await expect(page.locator('#search-results')).toContainText('匹配原文');
  await expect(page.locator('#search-results')).toContainText('定位到中文章节');
  await expect(page.locator('#search-results a')).toHaveAttribute('href','/SRD/core-resources/classes/');
  expect(await page.locator('#search-dialog').evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true);
});
