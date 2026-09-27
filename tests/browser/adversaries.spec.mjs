import {test, expect} from '@playwright/test';

async function selectFilter(page, key, value) {
  const dropdown = page.locator(`.filter-dropdown[data-filter="${key}"]`);
  if (!(await dropdown.getAttribute('open') !== null)) await dropdown.locator('summary').click();
  await dropdown.locator(`button[data-value="${value}"]`).click();
}

test('combined filters, bilingual names, view, language and reset', async ({page}) => {
  await page.goto('/SRD/adversaries-and-environments/adversary-data/');
  await expect(page.locator('#catalog-count')).toHaveText('139 / 139 个敌人');
  const toolTops = await page.locator('#catalog-filters > *').evaluateAll(elements => elements.map(element => Math.round(element.getBoundingClientRect().top)));
  expect(new Set(toolTops).size).toBe(1);
  await expect(page.getByText('主持人工具 / 敌人', {exact: true})).toHaveCount(0);
  await page.screenshot({path: 'test-results/adversaries-desktop.png', fullPage: false});
  await page.locator('#adversary-query').fill('锯齿刀');
  await selectFilter(page, 'tier', '1');
  await selectFilter(page, 'type', 'standard');
  await expect(page.locator('.adversary:visible')).toHaveCount(1);
  await expect(page.locator('.adversary:visible')).toHaveAttribute('id', 'adversary-jagged-knife-bandit');
  await page.locator('#adversary-view').press('ArrowLeft');
  await expect(page.locator('.adversary:visible .lang-zh .stat-content')).toBeVisible();
  await page.locator('#adversary-view').press('ArrowRight');
  await expect(page.locator('.adversary:visible .lang-zh .stat-content')).toBeHidden();
  await page.locator('#adversary-view').press('ArrowLeft');
  await page.locator('#adversary-jagged-knife-bandit').screenshot({path: 'test-results/adversary-card.png'});
  await page.locator('#language-button').click();
  await expect(page.locator('#catalog-count')).toHaveText('1 / 139 adversaries');
  await expect(page.locator('#adversary-query')).toHaveValue('锯齿刀');
  await page.reload();
  await expect(page.locator('.adversary:visible')).toHaveCount(1);
  await page.locator('#adversary-query').fill('no such creature');
  await expect(page.locator('#catalog-empty')).toBeVisible();
  await page.locator('button[type=reset]').click();
  await expect(page.locator('.adversary:visible')).toHaveCount(139);
  await page.locator('#adversary-query').fill('  bEaR  ');
  await expect(page.locator('#adversary-bear')).toBeVisible();
});

test.describe('Markdown editor', () => {
  test.use({httpCredentials: {username: 'admin', password: 'playwright'}});
  test('edit existing Markdown, preview the card and publish the same source', async ({page}) => {
    let publication;
    await page.route('**/SRD/api/save', async route => {
      publication = route.request().postDataJSON();
      await route.fulfill({json: {versions: Object.fromEntries(publication.changes.map(item => [item.path, 'next'])), gitSync: {status: 'synced'}}});
    });
    await page.goto('/SRD/edit/?path=adversaries-and-environments/adversary-data');
    await expect(page.locator('#preview .stat-card')).toHaveCount(139);
    const textarea = page.locator('#editor-textarea');
    const original = await textarea.inputValue();
    expect(original).toContain('<!-- adversary: jagged-knife-bandit |');
    await textarea.fill(original.replace('**难度：** 12', '**难度：** 27').replace('锯齿刀盗贼攀爬起来和奔跑一样轻松。', '编辑器同步验证。'));
    const card = page.locator('#preview [data-card-id="jagged-knife-bandit"]');
    await expect(card).toHaveAttribute('data-difficulty', '27');
    await expect(card).toContainText('编辑器同步验证。');
    await card.scrollIntoViewIfNeeded();
    await page.screenshot({path: 'test-results/adversaries-editor.png'});
    await page.locator('#save-btn').click();
    await page.locator('#publish-name').fill('浏览器测试');
    await page.getByRole('button', {name: '确认发布', exact: true}).click();
    await expect(page.locator('#save-status')).toHaveText('已同步至 GitHub');
    expect(publication.changes).toHaveLength(1);
    expect(publication.changes[0].path).toBe('src/pages/adversaries-and-environments/adversary-data/zh.md');
    expect(publication.changes[0].content).toContain('**难度：** 27');
    expect(publication.changes[0].content).toContain('<!-- /adversary -->');
  });
});

test('deep links clear conflicting filters and historical anchors still resolve', async ({page}) => {
  await page.goto('/SRD/adversaries-and-environments/adversary-data/?tier=4#adversary-bear');
  await expect(page.locator('#adversary-bear')).toBeVisible();
  await expect(page.locator('#adversary-bear .lang-zh .stat-content')).toBeVisible();
  const legacy = await page.locator('#adversary-bear .lang-zh h3').getAttribute('id');
  await page.goto(`/SRD/adversaries-and-environments/adversary-data/?tier=4#${legacy}`);
  await expect(page.locator('#adversary-bear')).toBeVisible();
  await page.goto('/SRD/adversaries/#bear');
  await expect(page).toHaveURL(/adversary-data\/#adversary-bear$/);
});

test('mobile layout, missing English fallback, home and search entry', async ({page}) => {
  await page.setViewportSize({width: 390, height: 844});
  await page.goto('/SRD/');
  await page.locator('.home-note a[href="/SRD/adversaries-and-environments/adversary-data/"]').click();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.locator('#adversary-query').fill('Briarwhip');
  await page.locator('#adversary-view').press('ArrowLeft');
  await page.locator('#language-button').click();
  await expect(page.locator('.adversary:visible .adversary-notice')).toBeVisible();
  await page.locator('#theme-button').click();
  await expect(page.locator('.adversary:visible')).toHaveCount(1);
  await page.screenshot({path: 'test-results/adversaries-mobile.png', fullPage: true});
  const search = await (await page.request.get('/SRD/generated/search-index.json')).json();
  expect(search.records.filter(record => record.path === 'adversaries-and-environments/adversary-data')).toHaveLength(278);
});

test('site search opens the complete catalog entry', async ({page}) => {
  await page.goto('/SRD/');
  await page.locator('#search-button').click();
  await page.locator('#search-input').fill('锯齿刀盗贼');
  await page.locator('#search-results a[href="/SRD/adversaries-and-environments/adversary-data/#adversary-jagged-knife-bandit"]').click();
  await expect(page.locator('#adversary-jagged-knife-bandit .lang-zh .stat-content')).toBeVisible();
  await expect(page.locator('#adversary-jagged-knife-bandit .lang-zh .stat-content')).toContainText('如履平地');
});

test('complete blocks remain readable without JavaScript', async ({browser}) => {
  const context = await browser.newContext({javaScriptEnabled: false});
  const page = await context.newPage();
  await page.goto('http://127.0.0.1:8766/SRD/adversaries-and-environments/adversary-data/');
  await expect(page.locator('#adversary-bear .lang-zh .stat-content')).toBeVisible();
  await expect(page.locator('#catalog-filters')).toBeHidden();
  await context.close();
});

test('tier and type selections combine as OR within each group and survive reload', async ({page}) => {
  await page.goto('/SRD/adversaries-and-environments/adversary-data/');
  for (const tier of ['1', '2']) await selectFilter(page, 'tier', tier);
  for (const role of ['leader', 'minion']) await selectFilter(page, 'type', role);
  const selected = await page.locator('.adversary:visible').evaluateAll(cards => cards.map(card => [card.dataset.tier, card.dataset.type]));
  expect(selected.length).toBeGreaterThan(4);
  expect(selected.every(([tier, type]) => ['1', '2'].includes(tier) && ['leader', 'minion'].includes(type))).toBe(true);
  await page.reload();
  await expect(page.locator('.adversary:visible')).toHaveCount(selected.length);
  await page.locator('#language-button').click();
  await expect(page.locator('#adversary-type button[aria-pressed=true]')).toHaveCount(2);
  await selectFilter(page, 'tier', '1');
  expect(await page.locator('.adversary:visible').evaluateAll(cards => cards.every(card => card.dataset.tier === '2'))).toBe(true);
  await page.locator('button[type=reset]').click();
  await expect(page.locator('.adversary:visible')).toHaveCount(139);
});

test('compact strips show canonical stats and hover preview remains readable', async ({page}) => {
  await page.goto('/SRD/adversaries-and-environments/adversary-data/?view=list&tier=1');
  const card = page.locator('#adversary-bear');
  await expect(card.locator('.compact-stats')).toContainText('难 14');
  await expect(card.locator('.compact-stats')).toContainText('阈 9/17');
  await expect(card.locator('.compact-stats')).toContainText('命 7');
  await expect(card.locator('.compact-stats')).toContainText('压 2');
  const full = card.locator('.lang-zh');
  await expect(full.locator('.stat-heading .stat-description')).toContainText('巨熊');
  await expect(full.locator('.stat-resources')).toContainText('生命点');
  await expect(full.locator('.stat-resource')).toHaveCount(0);
  await expect(card.locator('.compact-tier')).toHaveText('T1');
  expect((await card.boundingBox()).height).toBeLessThan(65);
  await expect(page.locator('.stat-footer')).toHaveCount(0);
  await card.hover();
  const preview = page.locator('#adversary-preview');
  await expect(preview).toBeVisible();
  const resourceRows = await preview.locator('.stat-resources > span').evaluateAll(elements => elements.map(element => Math.round(element.getBoundingClientRect().top)));
  expect(new Set(resourceRows).size).toBe(1);
  await expect(preview.locator('.stat-content')).toHaveText(await card.locator('.lang-zh .stat-content').textContent());
  await preview.hover();
  await expect(preview).toBeVisible();
  const bounds = await preview.boundingBox();
  expect(bounds.x).toBeGreaterThanOrEqual(0);
  expect(bounds.x + bounds.width).toBeLessThanOrEqual(1280);
  expect(bounds.y + bounds.height).toBeLessThanOrEqual(720);
  expect(await page.locator('[id]').evaluateAll(elements => new Set(elements.map(el => el.id)).size === elements.length)).toBe(true);
  await page.screenshot({path: 'test-results/adversaries-compact-hover.png'});
  await page.keyboard.press('Escape');
  await expect(preview).toBeHidden();
  await card.locator('.compact-name').focus();
  await expect(preview).toBeVisible();
  await card.locator('.compact-name').click();
  await expect(page).toHaveURL(/#adversary-bear$/);
  await expect(card.locator('.lang-zh .stat-content')).toBeVisible();
});

test('mobile compact strip fits the screen and opens by tapping the name', async ({page}) => {
  await page.setViewportSize({width: 390, height: 844});
  await page.goto('/SRD/adversaries-and-environments/adversary-data/?view=list&q=Bear');
  const card = page.locator('#adversary-bear');
  await expect(card.locator('.compact-stats')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect((await card.boundingBox()).height).toBeLessThan(65);
  await card.locator('.compact-name').click();
  await expect(card.locator('.lang-zh .stat-content')).toBeVisible();
  await expect(page.locator('#adversary-preview')).toBeHidden();
});

test('stat labels sit above unbroken values at desktop and narrow widths', async ({page}) => {
  await page.goto('/SRD/adversaries-and-environments/adversary-data/');
  for (const width of [1280, 390, 320]) {
    await page.setViewportSize({width, height: 844});
    const failures = await page.locator('.adversary .lang-zh .stat-values > span').evaluateAll(cells => cells.flatMap(cell => {
      const number = [...cell.childNodes].find(node => node.nodeType === Node.TEXT_NODE && node.textContent.trim());
      const range = document.createRange();
      range.selectNodeContents(number);
      const value = range.getBoundingClientRect();
      const label = cell.querySelector('strong').getBoundingClientRect();
      return range.getClientRects().length !== 1 || label.bottom > value.top + 1 || value.right > cell.getBoundingClientRect().right + 1 ? [cell.textContent] : [];
    }));
    expect(failures).toEqual([]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
});

test('search keeps card width and sliding switch preserves the filter', async ({page}) => {
  await page.goto('/SRD/adversaries-and-environments/adversary-data/');
  await expect(page.locator('#adversary-sort')).toHaveCount(0);
  const card = page.locator('#adversary-bear');
  const originalWidth = (await card.boundingBox()).width;
  await page.locator('#adversary-query').fill('一只毛皮厚实');
  await expect(page.locator('.adversary:visible')).toHaveCount(1);
  expect((await card.boundingBox()).width).toBeCloseTo(originalWidth, 0);
  const toggle = page.getByRole('switch', {name: '紧凑视图'});
  await toggle.click();
  await expect(toggle).toHaveAttribute('aria-checked', 'true');
  await expect(card.locator('.compact-entry')).toBeVisible();
  await expect(page.locator('#adversary-query')).toHaveValue('一只毛皮厚实');
  await toggle.click();
  await expect(toggle).toHaveAttribute('aria-checked', 'false');
  expect((await card.boundingBox()).width).toBeCloseTo(originalWidth, 0);
  await page.screenshot({path: 'test-results/adversary-fixed-width-switch.png'});
});

test('fixed card columns, full-text filtering and feature-only glossary', async ({page}) => {
  await page.goto('/SRD/adversaries-and-environments/adversary-data/');
  await page.setViewportSize({width: 1920, height: 1080});
  const tops = await page.locator('[data-tier-group="1"] .adversary').evaluateAll(cards => cards.slice(0, 5).map(card => Math.round(card.getBoundingClientRect().top)));
  expect(new Set(tops.slice(0, 3)).size).toBe(1);
  expect(tops[3]).toBeGreaterThan(tops[0]);
  const terms = page.locator('.adversary .term-link');
  expect(await terms.count()).toBeGreaterThan(0);
  expect(await terms.evaluateAll(items => items.every(item => item.closest('.stat-features') && !item.closest('.no-glossary')))).toBe(true);
  await page.locator('#adversary-query').fill('居高临下');
  await expect(page.locator('#adversary-jagged-knife-bandit')).toBeVisible();
  await expect(page.locator('#adversary-bear')).toBeHidden();
  await page.locator('#adversary-query').fill('9/17');
  await expect(page.locator('#adversary-bear')).toBeVisible();
  await page.locator('#adversary-query').fill('');
  await page.screenshot({path: 'test-results/adversaries-three-columns.png'});
});

test('phrase search ignores spacing and highlights inline glossary text', async ({page}) => {
  await page.goto('/SRD/adversaries-and-environments/adversary-data/');
  const query = page.locator('#adversary-query');
  await query.fill('花费 2 恐惧点');
  await expect(page.locator('#adversary-head-guard')).toBeVisible();
  await expect(page.locator('#adversary-acid-burrower')).toBeHidden();
  const ids = await page.locator('.adversary:visible').evaluateAll(cards => cards.map(card => card.id));
  expect(ids.length).toBeGreaterThan(0);
  const guard = page.locator('#adversary-head-guard .lang-zh');
  expect((await guard.locator('mark').allTextContents()).join('').replace(/\s/g, '')).toContain('花费2恐惧点');
  await expect(guard.locator('.term-link mark').first()).toBeVisible();
  await query.fill('花费2恐惧点');
  expect(await page.locator('.adversary:visible').evaluateAll(cards => cards.map(card => card.id))).toEqual(ids);
  await page.locator('#adversary-view').click();
  await page.locator('#adversary-head-guard').hover();
  await expect(page.locator('#adversary-preview mark').first()).toBeVisible();
  await page.screenshot({path: 'test-results/adversary-search-highlight.png'});
  await query.fill('');
  await expect(page.locator('#adversary-results mark')).toHaveCount(0);
});
