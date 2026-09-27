import {test} from 'node:test';
import assert from 'node:assert/strict';
import {phraseMatches} from '../static/js/adversary-search.mjs';

test('formatting spaces do not change phrase matching or highlight offsets', () => {
  const text = '可以花费  2\n恐惧点，然后行动。';
  for (const query of ['花费 2 恐惧点', '花费2恐惧点', '花费　２　恐惧点']) {
    const hits = phraseMatches(text, query);
    assert.equal(hits.length, 1);
    assert.equal(text.slice(...hits[0]), '花费  2\n恐惧点');
  }
});

test('separate words and different costs do not match the phrase', () => {
  assert.deepEqual(phraseMatches('花费 1 恐惧点，造成 2 点伤害。', '花费 2 恐惧点'), []);
  assert.deepEqual(phraseMatches('花费 12 恐惧点', '花费 2 恐惧点'), []);
  assert.deepEqual(phraseMatches('花费 2 恐惧点', '   '), []);
  assert.equal(phraseMatches('BEAR bear', 'Bear').length, 2);
});
