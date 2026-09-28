import { expect, test } from '@playwright/test';
const root = '/SRD/core-mechanics/equipment/';
const active = page => page.locator('.equipment-catalog:visible');
const rows = page => active(page).locator('tbody tr:visible');

async function choose(page, column, value) {
  await page.getByRole('button',{name:`筛选${column}`,exact:true}).click();
  const dialog = page.getByRole('dialog',{name:`筛选 ${column}`,exact:true});
  await dialog.getByRole('button',{name:'全不选',exact:true}).click();
  await dialog.getByRole('checkbox',{name:value,exact:true}).check();
  await page.keyboard.press('Escape');
}

test('主武器多列表头筛选、双语文字查找、排序与语言切换', async ({page}) => {
  await page.goto(root+'primary-weapons/');
  await expect(rows(page)).toHaveCount(155);
  await choose(page,'位阶','1');
  await expect(rows(page)).toHaveCount(25);
  await choose(page,'类型','魔法');
  await expect(rows(page)).toHaveCount(10);
  await page.getByRole('button',{name:'按伤害排序',exact:true}).click();
  await expect(active(page).locator('th[data-column="damage"]')).toHaveAttribute('aria-sort','ascending');
  const values = await rows(page).locator('[data-column="damage"]').evaluateAll(cells => cells.map(c => c.dataset.value.match(/\d+/g).map(Number)));
  expect(values).toEqual([...values].sort((a,b)=>a[0]-b[0]||(a[1]||0)-(b[1]||0)));
  await page.getByRole('button',{name:'查询名称',exact:true}).click();
  await page.getByRole('dialog').getByRole('searchbox').fill('Gauntlets');
  await expect(rows(page)).toHaveCount(1);
  await expect(rows(page).first()).toContainText('奥术护手');
  await page.keyboard.press('Escape');
  await page.locator('#language-button').click();
  await expect(rows(page)).toHaveCount(1);
  await expect(rows(page).first()).toContainText('Arcane');
  await page.getByRole('button',{name:'Reset filters and sorting'}).click();
  await expect(rows(page)).toHaveCount(155);
  await expect(active(page).locator('th[data-column="damage"]')).toHaveAttribute('aria-sort','none');
});

test('副武器与护甲保留所有条目，护甲值与阈值按数值排序',async ({page}) => {
  await page.goto(root+'secondary-weapons/');
  await expect(rows(page)).toHaveCount(37);
  await expect(active(page).locator('th[data-column="type"]')).toContainText('类型');
  for (const type of await rows(page).locator('[data-column="type"]').allTextContents()) expect(type).toBe('物理');
  await page.locator('#language-button').click();
  for (const damage of await rows(page).locator('[data-column="damage"]').allTextContents()) expect(damage).not.toMatch(/\b(?:phy|mag)\b/);
  for (const type of await rows(page).locator('[data-column="type"]').allTextContents()) expect(type).toBe('Physical');
  await page.locator('#language-button').click();
  await page.goto(root+'armor/');
  await expect(rows(page)).toHaveCount(34);
  const sort = page.getByRole('button',{name:'按护甲值排序',exact:true});
  await sort.click(); await sort.click();
  await expect(rows(page).first().locator('[data-column="armor"]')).toHaveText('8');
  await sort.click();
  await page.getByRole('button',{name:'按阈值排序',exact:true}).click();
  await expect(rows(page).first().locator('[data-column="thresholds"]')).toHaveText('5 / 11');
  await choose(page,'护甲值','8');
  await page.getByRole('button',{name:'查询特性',exact:true}).click();
  await page.getByRole('dialog').getByRole('searchbox').fill('不存在的特性');
  await expect(rows(page)).toHaveCount(0);
  await expect(active(page).locator('.equipment-empty')).toBeVisible();
  await page.keyboard.press('Escape');
  await page.getByRole('button',{name:'清除筛选与排序'}).click();
  await expect(rows(page)).toHaveCount(34);
});

for (const kind of ['items','consumables']) {
  test(`${kind} 完整 60 条，所有字段通过放大镜查询并保留双语与旧链接`,async ({page})=>{
    await page.goto(root+(kind==='items'?'#loot':'#consumables'));
    await expect(page).toHaveURL(new RegExp(`/${kind}/#`));
    await expect(rows(page)).toHaveCount(60);
    const catalog=active(page);
    await expect(catalog.locator('th[data-filter="choices"]')).toHaveCount(0);
    await expect(catalog.locator('th .equipment-icon-search')).toHaveCount(3);
    await page.getByRole('button',{name:'查询掷骰编号',exact:true}).click();
    await expect(page.getByRole('dialog').getByRole('checkbox')).toHaveCount(0);
    await page.getByRole('dialog').getByRole('searchbox').fill('10');
    await expect(rows(page)).toHaveCount(1);
    await expect(rows(page).locator('[data-column="roll"]')).toHaveText('10');
    await page.keyboard.press('Escape');
    await page.getByRole('button',{name:'清除查询与排序'}).click();
    if(kind==='items') {
      await page.getByRole('button',{name:'查询名称',exact:true}).click();
      await page.getByRole('dialog').getByRole('searchbox').fill('Gecko Gloves');
      await expect(rows(page)).toHaveCount(1);
      await expect(rows(page)).toContainText('壁虎手套');
      await page.keyboard.press('Escape');
      await page.getByRole('button',{name:'清除查询与排序'}).click();
    }
    await page.screenshot({path:`test-results/equipment-${kind}.png`});
    await page.locator('#language-button').click();
    await expect(rows(page)).toHaveCount(60);
    await expect(page.locator('html')).toHaveAttribute('lang','en');
    await page.setViewportSize({width:390,height:844});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  });
}

test('伤害和阈值使用文字查询，不再列出数字复选框',async ({page}) => {
  await page.goto(root+'primary-weapons/');
  await page.getByRole('button',{name:'查询伤害',exact:true}).click();
  let dialog=page.getByRole('dialog');
  await expect(dialog.getByRole('checkbox')).toHaveCount(0);
  await dialog.getByRole('searchbox').fill('d10+3');
  await expect(rows(page)).not.toHaveCount(0);
  const damage=await rows(page).locator('[data-column="damage"]').allTextContents();
  expect(damage.every(value=>value.replace(/\s/g,'').includes('d10+3'))).toBe(true);
  await page.keyboard.press('Escape');
  await page.goto(root+'armor/');
  await page.getByRole('button',{name:'查询阈值',exact:true}).click();
  dialog=page.getByRole('dialog');
  await expect(dialog.getByRole('checkbox')).toHaveCount(0);
  await dialog.getByRole('searchbox').fill('11 / 24');
  await expect(rows(page)).not.toHaveCount(0);
  for(const text of await rows(page).locator('[data-column="thresholds"]').allTextContents()) expect(text.replace(/\s/g,'')).toContain('11/24');
});

test('多列排序按点击次序叠加，降序和取消不影响其他列',async ({page}) => {
  await page.goto(root+'primary-weapons/');
  const headers=active(page).locator('th');
  expect(await headers.evaluateAll(items=>items.map(el=>el.dataset.column))).toEqual(['name','tier','trait','range','damage','type','burden','feature']);
  for(const key of ['name','feature']) await expect(active(page).locator(`th[data-column="${key}"] .equipment-icon-search`)).toHaveCount(1);
  const initialWidths=await headers.evaluateAll(items=>items.map(el=>el.getBoundingClientRect().width));
  const tier=page.getByRole('button',{name:'按位阶排序',exact:true});
  const damage=page.getByRole('button',{name:'按伤害排序',exact:true});
  await tier.click();
  await damage.click(); await damage.click();
  await expect(active(page).locator('th[data-column="tier"]')).toHaveAttribute('data-sort-priority','1');
  await expect(active(page).locator('th[data-column="damage"]')).toHaveAttribute('data-sort-priority','2');
  await expect(active(page).locator('.equipment-sort-summary')).toHaveText('排序：1 位阶 ↑ · 2 伤害 ↓');
  await expect(active(page).locator('.equipment-sort-priority')).toHaveCount(0);
  const sortedWidths=await headers.evaluateAll(items=>items.map(el=>el.getBoundingClientRect().width));
  sortedWidths.forEach((width,i)=>expect(Math.abs(width-initialWidths[i])).toBeLessThan(1));
  const values=await rows(page).evaluateAll(items=>items.map(row=>[Number(row.querySelector('[data-column="tier"]').dataset.value),...row.querySelector('[data-column="damage"]').dataset.value.match(/\d+/g).map(Number)]));
  expect(values).toEqual([...values].sort((a,b)=>a[0]-b[0]||b[1]-a[1]||(b[2]||0)-(a[2]||0)));
  await page.screenshot({path:'test-results/equipment-multisort.png'});
  await tier.click(); await tier.click();
  await expect(active(page).locator('th[data-column="tier"]')).toHaveAttribute('aria-sort','none');
  await expect(active(page).locator('th[data-column="damage"]')).toHaveAttribute('data-sort-priority','1');
  await page.locator('#language-button').click();
  await expect(active(page).locator('.equipment-sort-summary')).toHaveText('Sort: 1 Damage ↓');
  await page.getByRole('button',{name:'Reset filters and sorting'}).click();
  await expect(active(page).locator('th[data-column="damage"]')).toHaveAttribute('aria-sort','none');
});

test('表头下拉图标居中且手机弹层不超出屏幕',async ({page}) => {
  await page.setViewportSize({width:390,height:844});
  await page.goto(root+'primary-weapons/');
  const button=page.getByRole('button',{name:'筛选位阶',exact:true});
  const metrics=await button.evaluate(el=>{
    const a=el.getBoundingClientRect(),b=el.querySelector('svg').getBoundingClientRect();
    return {x:Math.abs(a.x+a.width/2-b.x-b.width/2),y:Math.abs(a.y+a.height/2-b.y-b.height/2)};
  });
  expect(metrics.x).toBeLessThanOrEqual(1);
  expect(metrics.y).toBeLessThanOrEqual(1);
  await button.click();
  const box=await page.getByRole('dialog').boundingBox();
  expect(box.x).toBeGreaterThanOrEqual(0);
  expect(box.x+box.width).toBeLessThanOrEqual(390);
  await page.screenshot({path:'test-results/equipment-controls-mobile.png'});
});

test('装备目录分组、轮椅在文末，旧表格小节跳到正确子页', async ({page}) => {
  await page.goto(root);
  await expect(page.locator('.lang-zh h1').last()).toHaveText('战斗轮椅');
  await expect(page.locator('#contents-tree a[href="'+root+'primary-weapons/"]')).toBeVisible();
  await page.goto(root+'#magic-weapons');
  await expect(page).toHaveURL(/\/primary-weapons\/#magic-weapons$/);
  await expect(page.locator('#magic-weapons')).toHaveCount(1);
  await expect(page.locator('#magic-weapons').locator('xpath=ancestor::tr')).toContainText('奥术护手');
  await page.goto(root+'#tier-2-levels-24-4');
  await expect(page).toHaveURL(/\/armor\/#tier-2-levels-24-4$/);
  await expect(page.locator('#tier-2-levels-24-4').locator('xpath=ancestor::tr')).toContainText('改良填充布甲');
});

test('整站搜索定位单件装备，中英文显示同一装备', async ({page}) => {
  await page.goto('/SRD/');
  await page.locator('#search-button').click();
  await page.locator('#search-input').fill('Broadsword');
  const result=page.locator('#search-results a[href="'+root+'primary-weapons/#gear-tier-1-broadsword"]');
  await expect(result).toHaveCount(1);
  await expect(result.locator('h3')).toHaveText('阔剑');
  await result.click();
  await expect(page.locator('#gear-tier-1-broadsword')).toBeVisible();
  await page.locator('#language-button').click();
  await expect(page.locator('#gear-tier-1-broadsword')).toContainText('Broadsword');
});

test('手机筛选可用且横向滚动限制在表格内，桌面与夜间模式可读', async ({page}) => {
  await page.setViewportSize({width:1440,height:960});
  await page.goto(root+'primary-weapons/');
  await choose(page,'位阶','1');
  await page.screenshot({path:'test-results/equipment-desktop.png'});
  await page.setViewportSize({width:390,height:844});
  await choose(page,'属性','敏捷');
  await expect(rows(page)).not.toHaveCount(0);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect(await active(page).locator('.equipment-scroll').evaluate(el=>el.scrollWidth>el.clientWidth)).toBe(true);
  await page.screenshot({path:'test-results/equipment-mobile.png'});
  await page.locator('#theme-button').click();
  await page.getByRole('button',{name:'筛选位阶',exact:true}).click();
  const box=await page.getByRole('dialog').boundingBox();
  expect(box.x).toBeGreaterThanOrEqual(0);
  expect(box.x+box.width).toBeLessThanOrEqual(390);
  await page.screenshot({path:'test-results/equipment-mobile-dark.png'});
});

test('禁用 JavaScript 时仍可阅读完整装备表', async ({browser}) => {
  const context=await browser.newContext({javaScriptEnabled:false});
  const page=await context.newPage();
  await page.goto('http://127.0.0.1:8766'+root+'armor/');
  await expect(page.locator('.lang-zh .equipment-table tbody tr')).toHaveCount(34);
  await expect(page.locator('.lang-zh .equipment-toolbar')).toBeHidden();
  await context.close();
});

test.describe('equipment editor', () => {
  test.use({httpCredentials:{username:'admin',password:'playwright'}});
  test('编辑原 Markdown 后预览立即更新表格与数值排序数据', async ({page}) => {
    await page.goto('/SRD/edit/?path=core-mechanics/equipment/armor');
    await expect(page.locator('#preview .equipment-table tbody tr')).toHaveCount(34);
    const editor=page.locator('#editor-textarea');
    await editor.fill((await editor.inputValue()).replace(/(\| \*\*填充布甲\*\* \| 5 \/ 11 \|\s*)3/,'$19'));
    const score=page.locator('#preview .equipment-table tbody tr').first().locator('[data-column="armor"]');
    await expect(score).toHaveText('9');
    await expect(score).toHaveAttribute('data-value','9');
  });
});
