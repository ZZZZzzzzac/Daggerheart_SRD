import {test, expect} from '@playwright/test';
test('domain catalog filters, highlights, switch and preview', async ({page}) => {
  await page.goto('/SRD/domain-cards/');
  await expect(page.locator('#catalog-filters')).toBeVisible();
  expect(await page.locator('.adversary').count()).toBe(189);
  await page.locator('[data-filter=type] summary').click();
  await page.locator('#adversary-type button[data-value=arcana]').click();
  await page.locator('#adversary-type button[data-value=blade]').click();
  await page.locator('[data-filter=tier] summary').click();
  await page.locator('#adversary-tier button[data-value="1"]').click();
  await expect(page.locator('.adversary:visible')).toHaveCount(6);
  await page.locator('#adversary-query').fill('护身符');
  await expect(page.locator('.adversary:visible')).toHaveCount(1);
  await expect(page.locator('#domain-rune-ward .lang-zh mark').first()).toBeVisible();
  await page.locator('#adversary-view').click();
  await page.locator('#domain-rune-ward').hover();
  await expect(page.locator('#adversary-preview .domain-stats')).toBeVisible();
  await page.keyboard.press('Escape');
  await page.locator('button[type=reset]').click();
  await page.locator('[data-filter=cardtype] summary').click();
  await page.locator('#adversary-cardtype button[data-value="法术"]').click();
  expect(await page.locator('.adversary:visible').evaluateAll(cards => cards.every(card => card.dataset.cardType === '法术'))).toBe(true);
  await page.reload();
  await expect(page.locator('#adversary-cardtype button[data-value="法术"]')).toHaveAttribute('aria-pressed', 'true');
  await page.locator('button[type=reset]').click();
  await page.screenshot({path: 'test-results/domain-catalog.png'});
});
test('domain deep links preserve language and mobile layout', async ({page}) => {
  await page.goto('/SRD/domain-cards/?view=list#rune-ward');
  await expect(page.locator('#domain-rune-ward .lang-zh .stat-content')).toBeVisible();
  await page.locator('#language-button').click();
  await expect(page.locator('#domain-rune-ward .lang-en .domain-stats')).toBeVisible();
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test.describe('domain editor', () => {
  test.use({httpCredentials: {username:'admin',password:'playwright'}});
  test('Markdown edits update card metadata and content', async ({page}) => {
    await page.goto('/SRD/edit/?path=domain-cards');
    await expect(page.locator('#preview .domain-card')).toHaveCount(189);
    const editor = page.locator('#editor-textarea');
    await editor.fill((await editor.inputValue()).replace('回想费用：0', '回想费用：3'));
    await expect(page.locator('#preview .domain-card').first()).toHaveAttribute('data-recall','3');
    await expect(page.locator('#preview .domain-stats').first()).toContainText('3');
  });
});

test('domain lists keep bullets without feature-card borders, including hover preview', async ({page}) => {
  await page.goto('/SRD/domain-cards/?q=利刃恩泽');
  const list = page.locator('#domain-blade-touched .lang-zh .stat-content ul');
  await expect(list).toBeVisible();
  await expect(list).toHaveCSS('list-style-type', 'disc');
  const item = list.locator('li').first();
  await expect(item).toHaveCSS('border-top-width', '0px');
  await expect(item).toHaveCSS('background-color', 'rgba(0, 0, 0, 0)');
  await page.locator('#domain-blade-touched').screenshot({path: 'test-results/domain-list.png'});
  await page.locator('#adversary-view').click();
  await page.locator('#domain-blade-touched').hover();
  await expect(page.locator('#adversary-preview ul')).toHaveCSS('list-style-type', 'disc');
  await expect(page.locator('#adversary-preview li').first()).toHaveCSS('border-top-width', '0px');
});
