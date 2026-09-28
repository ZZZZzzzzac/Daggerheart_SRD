import { expect, test } from '@playwright/test';

test('战斗轮椅属于装备页，目录与双语搜索不再出现独立页面', async ({ page }) => {
  await page.goto('/SRD/core-mechanics/equipment/#combat-wheelchair');
  await expect(page.locator('#combat-wheelchair')).toHaveText('战斗轮椅');
  await expect(page.locator('#contents-tree a[href="/SRD/core-mechanics/combat-wheelchair/"]')).toHaveCount(0);
  await expect(page.locator('#contents-tree a[href="/SRD/core-mechanics/equipment/#combat-wheelchair"]')).toBeVisible();
  await page.locator('#language-button').click();
  await expect(page.locator('#combat-wheelchair')).toHaveText('Combat Wheelchair');
  await expect(page.locator('#wheelchair-burden')).toHaveText('BURDEN');
  const index = await (await page.request.get('/SRD/generated/search-index.json')).json();
  expect(index.records.filter(record => record.path === 'core-mechanics/combat-wheelchair')).toHaveLength(0);
  expect(index.records.filter(record => record.path === 'core-mechanics/equipment' && record.anchor === 'combat-wheelchair')).toHaveLength(2);
});

test('旧轮椅小节链接跳到装备页，并保持英文阅读语言', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('dh-srd-lang', 'en'));
  await page.goto('/SRD/core-mechanics/combat-wheelchair/#burden');
  await expect(page).toHaveURL(/\/equipment\/#wheelchair-burden$/);
  await expect(page.locator('#wheelchair-burden')).toHaveText('BURDEN');
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
  await page.goto('/SRD/core-mechanics/combat-wheelchair/');
  await expect(page).toHaveURL(/\/equipment\/#combat-wheelchair$/);
});
