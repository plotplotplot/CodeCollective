const test = require('node:test');
const assert = require('node:assert/strict');
const filterUtils = require('../js/calendarFilterUtils.js');

const communityMap = {
  id: 'community_sectors',
  categories: [
    { label: 'Technology', matches: ['Tech Skills', 'AI'] },
    { label: 'Culture', matches: ['Culture', 'Community'] },
    { label: 'Other', matches: [] },
  ],
};

const techOnlyMap = {
  id: 'tech_only',
  categories: [
    { label: 'AI & ML', matches: ['AI'] },
    { label: 'General Tech', matches: [] },
  ],
};

test('unmapped events are hidden when excluded toggle is off', () => {
  const matched = filterUtils.eventMatchesTags({
    tags: ['Unknown Tag'],
    categoryMap: { ...communityMap, categories: communityMap.categories.filter((c) => c.label !== 'Other') },
    activeTagSlugs: new Set(['technology', 'culture']),
    showExcludedEvents: false,
  });
  assert.equal(matched, false);
});

test('unmapped events are shown when excluded toggle is on', () => {
  const matched = filterUtils.eventMatchesTags({
    tags: ['Unknown Tag'],
    categoryMap: { ...communityMap, categories: communityMap.categories.filter((c) => c.label !== 'Other') },
    activeTagSlugs: new Set(['technology', 'culture']),
    showExcludedEvents: true,
  });
  assert.equal(matched, true);
});

test('mapped event matches selected legend category', () => {
  const matched = filterUtils.eventMatchesTags({
    tags: ['AI'],
    categoryMap: communityMap,
    activeTagSlugs: new Set(['technology']),
    showExcludedEvents: false,
  });
  assert.equal(matched, true);
});

test('no selected legend categories means no mapped events are shown', () => {
  const matched = filterUtils.eventMatchesTags({
    tags: ['AI'],
    categoryMap: communityMap,
    activeTagSlugs: new Set(),
    showExcludedEvents: false,
  });
  assert.equal(matched, false);
});

test('tech_only map excludes non-tech dominant events', () => {
  const categories = filterUtils.getEffectiveMappedCategories(['Business', 'Community'], techOnlyMap);
  assert.equal(categories.length, 0);
});

test('tech_only map includes clear tech events', () => {
  const categories = filterUtils.getEffectiveMappedCategories(['AI'], techOnlyMap);
  assert.ok(categories.length > 0);
});
