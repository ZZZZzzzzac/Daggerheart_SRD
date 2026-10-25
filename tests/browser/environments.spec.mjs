import {test, expect} from '@playwright/test';
const path = '/SRD/adversaries-and-environments/environment-data/';

test('environment cards, multiselect, full-text highlights and compact preview', async ({page}) => {
  await page.goto(path);
  await expect(page.locator('#catalog-count')).toHaveText('47 / 47 个环境');
  await expect(page.locator('#adversary-results .environment-card')).toHaveCount(47);
  await expect(page.locator('.stat-resources')).toHaveCount(0);
  await expect(page.locator('.stat-meta .term-link, .environment-brief .term-link, .stat-heading .term-link')).toHaveCount(0);
  await page.locator('[data-filter="type"] summary').click();
  await page.locator('#adversary-type button[data-value="traversal"]').click();
  await page.locator('#adversary-type button[data-value="exploration"]').click();
  expect(await page.locator('.adversary:visible').evaluateAll(cards => cards.every(card => ['traversal', 'exploration'].includes(card.dataset.type)))).toBe(true);
  await page.locator('#adversary-query').fill('河床');
  await expect(page.locator('.adversary:visible')).toHaveCount(1);
  await expect(page.locator('#environment-raging-river .environment-question mark')).toBeVisible();
  await page.locator('#adversary-view').click();
  await page.locator('#environment-raging-river').hover();
  await expect(page.locator('#adversary-preview .environment-brief')).toBeVisible();
  await expect(page.locator('#adversary-preview mark')).toBeVisible();
  await page.keyboard.press('Escape');
  await page.locator('button[type=reset]').click();
  await page.locator('#language-button').click();
  await expect(page.locator('#catalog-count')).toHaveText('47 / 47 environments');
});

test('special difficulty, stable anchors, search entries and mobile width', async ({page}) => {
  await page.goto(path + '#environment-ambushed');
  await expect(page.locator('#environment-ambushed .lang-zh .environment-difficulty')).toContainText('特殊');
  const search = await (await page.request.get('/SRD/generated/search-index.json')).json();
  expect(search.records.filter(record => record.path === path.replace('/SRD/', '').replace(/\/$/, ''))).toHaveLength(94);
  await page.setViewportSize({width: 390, height: 844});
  await page.goto(path + '?q=汹涌河流');
  await expect(page.locator('#environment-raging-river')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({path: 'test-results/environment-mobile.png', fullPage: true});
  await page.setViewportSize({width: 1280, height: 900});
  await page.goto(path);
  await page.screenshot({path: 'test-results/environment-desktop.png'});
});

test.describe('environment editor', () => {
  test.use({httpCredentials: {username: 'admin', password: 'playwright'}});
  test('Markdown changes immediately update the shared environment template', async ({page}) => {
    await page.goto('/SRD/edit/?path=adversaries-and-environments/environment-data');
    await expect(page.locator('#preview .stat-card')).toHaveCount(47);
    const editor = page.locator('#editor-textarea');
    await editor.fill((await editor.inputValue()).replace(/(<!-- environment: raging-river \|[\s\S]*?<!-- \/environment -->)/, block => block.replace('**难度：** 10', '**难度：** 18')));
    await expect(page.locator('#preview [data-card-id="raging-river"]')).toHaveAttribute('data-difficulty', '18');
    await expect(page.locator('#preview [data-card-id="raging-river"] .environment-question').first()).toBeVisible();
  });
});


test('environment feature names retain heading styles in loose Markdown lists', async ({page}) => {
  await page.goto(path);
  {
    const names = page.locator('.lang-zh .stat-features em.no-glossary');
    expect(await names.count()).toBeGreaterThan(100);
    const styles = await names.evaluateAll(elements => elements.map(element => {
      const style = getComputedStyle(element);
      return {weight: style.fontWeight, fontStyle: style.fontStyle, color: style.color};
    }));
    for (const style of styles) {
      expect(style.weight).toBe('750');
      expect(style.fontStyle).toBe('normal');
      expect(style.color).toBe('rgb(100, 31, 29)');
    }
  }
  await expect(page.locator('.lang-zh .environment-question em').first()).toHaveCSS('font-style', 'italic');
  await expect(page.locator('.lang-zh .environment-question em').first()).toHaveCSS('font-weight', '400');
});
