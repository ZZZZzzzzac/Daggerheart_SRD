import {test, expect} from '@playwright/test';

test('SRD 2.0 transformations have six paired entries in the existing navigation', async ({page}) => {
  await page.goto('/SRD/core-resources/transformations/');
  for (const name of ['demigod','ghost','reanimated','shapeshifter','vampire','werewolf']) {
    await expect(page.locator(`#section-${name}`)).toBeVisible();
  }
  await page.locator('#language-button').click();
  await expect(page.locator('#section-demigod')).toHaveText('DEMIGOD');
  await expect(page.locator('#contents-tree a[href="/SRD/core-resources/transformations/"]')).toBeVisible();
});

test('new Dread domain filters and searches all 21 bilingual cards', async ({page}) => {
  await page.goto('/SRD/domain-cards/');
  const cards = page.locator('#adversary-results .domain-entry');
  await expect(cards).toHaveCount(210);
  await page.locator('[data-filter=type] summary').click();
  await page.locator('#adversary-type button[data-value=dread]').click();
  await expect(cards.filter({visible:true})).toHaveCount(21);
  await page.locator('#language-button').click();
  await expect(cards.filter({visible:true})).toHaveCount(21);
  await expect(cards.filter({visible:true}).first().locator('.lang-en .domain-stats')).toContainText('Dread');
  const index = await (await page.request.get('/SRD/generated/search-index.json')).json();
  expect(index.records.filter(record => record.path === 'domain-cards')).toHaveLength(420);
});


test('campaign topics are separate bilingual pages in navigation and search', async ({page}) => {
  await page.goto('/SRD/campaign-frames/');
  await expect(page.locator('#contents-tree .tree-page-link[href^="/SRD/campaign-frames/"]')).toHaveCount(16);
  await expect(page.locator('.lang-zh #section-western-campaigns')).toHaveText('');
  await page.locator('.srd-language.lang-zh a[href="/SRD/campaign-frames/western-campaigns/"]').click();
  await expect(page.locator('#section-western-campaigns')).toHaveText('');
  await expect(page.locator('.srd-article h1 .lang-zh')).toHaveText('西部战役');
  await expect(page.locator('.srd-article h1')).toHaveCount(1);
  await expect(page.locator('.lang-zh table').first()).toBeVisible();
  await page.locator('#language-button').click();
  await expect(page.locator('#section-western-campaigns')).toHaveText('');
  await expect(page.locator('.srd-article h1 .lang-en')).toHaveText('WESTERN CAMPAIGNS');
  await expect(page.locator('.srd-article h1')).toHaveCount(1);
  const index = await (await page.request.get('/SRD/generated/search-index.json')).json();
  expect(index.records.some(record => record.path === 'campaign-frames/western-campaigns' && record.anchor === 'section-weapons-loot')).toBe(true);
  expect(index.records.some(record => record.path === 'campaign-frames' && record.anchor === 'section-weapons-loot')).toBe(false);
});

test('old campaign section URLs retain their destination, query and reading language', async ({page}) => {
  await page.goto('/SRD/campaign-frames/?from=bookmark#section-harvesting-ingredients');
  await expect(page).toHaveURL('/SRD/campaign-frames/feasts/?from=bookmark#section-harvesting-ingredients');
  await expect(page.locator('#section-harvesting-ingredients')).toHaveText('采集食材');
  await page.locator('#language-button').click();
  await expect(page.locator('#section-harvesting-ingredients')).toHaveText('HARVESTING INGREDIENTS');
  await page.goto('/SRD/campaign-frames/#the-witherwild');
  await expect(page).toHaveURL('/SRD/campaign-frames/the-witherwild/#section-the-witherwild');
  await expect(page.locator('html')).toHaveAttribute('lang','en');
  await expect(page.locator('#section-the-witherwild')).toHaveText('');
  await expect(page.locator('.srd-article h1 .lang-en')).toHaveText('The Witherwild');
  await expect(page.locator('.srd-article h1')).toHaveCount(1);
});
