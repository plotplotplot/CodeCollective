(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
    return;
  }
  root.CalendarFilterUtils = factory();
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  function slugifyTag(tag) {
    return String(tag || '')
      .toLowerCase()
      .replace(/&/g, 'and')
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '');
  }

  function normalizeMapCategory(category) {
    return {
      label: category.label,
      slug: slugifyTag(category.label),
      matchSlugs: new Set((category.matches || []).map(slugifyTag).filter(Boolean)),
    };
  }

  function getOtherCategory(categoryMap) {
    return (categoryMap?.categories || [])
      .map(normalizeMapCategory)
      .find((category) => category.slug === 'other') || null;
  }

  function getDirectMappedCategoriesForTags(tags, categoryMap) {
    const normalizedTags = Array.isArray(tags) ? tags.map(slugifyTag).filter(Boolean) : [];
    const mappedCategories = (categoryMap?.categories || [])
      .map(normalizeMapCategory)
      .filter((category) => normalizedTags.some((tag) => category.matchSlugs.has(tag)));

    if (mappedCategories.length > 0) {
      return mappedCategories;
    }

    const otherCategory = getOtherCategory(categoryMap);
    return otherCategory ? [otherCategory] : [];
  }

  function isTechOnlyEvent(tags) {
    const normalizedTags = new Set((Array.isArray(tags) ? tags : []).map(slugifyTag).filter(Boolean));
    if (normalizedTags.size === 0) return false;

    const specificTechTags = new Set([
      'ai',
      'data-science',
      'cybersecurity',
      'cloud-and-platform',
      'devops',
      'software-development',
      'web-development',
      'javascript',
      'python',
      'ruby',
      'open-source',
      'technical-writing',
      'game-development',
      'ux',
      'product',
      'crypto-and-web3',
      'makerspace',
      'robotics',
      'civic-tech',
    ]);
    const genericTechTags = new Set([
      'tech-skills',
      'tech-community',
      'code-collective-and-partners',
    ]);
    const dominantNonTechTags = new Set([
      'water',
      'water-and-environment',
      'religion',
      'culture',
      'community',
      'politics',
      'food',
      'housing',
      'shelter-and-habitat',
      'clothing',
      'survival-and-health',
      'safety-and-stability',
      'belonging-and-culture',
      'purpose-and-service',
      'faith-and-spirituality',
      'business',
      'economic-development',
      'professional-networking',
      'career-growth',
      'startup',
      'waterfront',
      'infrastructure',
      'finance',
    ]);

    if (Array.from(normalizedTags).some((tag) => specificTechTags.has(tag))) {
      return true;
    }

    if (!Array.from(normalizedTags).some((tag) => genericTechTags.has(tag))) {
      return false;
    }

    if (Array.from(normalizedTags).some((tag) => dominantNonTechTags.has(tag))) {
      return false;
    }

    return true;
  }

  function getEffectiveMappedCategories(tags, categoryMap) {
    if (categoryMap?.id === 'tech_only' && !isTechOnlyEvent(tags)) {
      return [];
    }
    return getDirectMappedCategoriesForTags(tags, categoryMap);
  }

  function isExcludedFromActiveMap(tags, categoryMap) {
    if (categoryMap?.id === 'tech_only' && !isTechOnlyEvent(tags)) {
      return true;
    }
    return getDirectMappedCategoriesForTags(tags, categoryMap).length === 0;
  }

  function eventMatchesTags(params) {
    const tags = params?.tags;
    const categoryMap = params?.categoryMap;
    const activeTagSlugs = params?.activeTagSlugs;
    const showExcludedEvents = params?.showExcludedEvents === true;

    const mappedCategories = getEffectiveMappedCategories(tags, categoryMap);
    if (mappedCategories.length === 0) {
      return showExcludedEvents;
    }
    if (!activeTagSlugs || activeTagSlugs.size === 0) return false;
    return mappedCategories.some((category) => activeTagSlugs.has(category.slug));
  }

  return {
    slugifyTag,
    normalizeMapCategory,
    getOtherCategory,
    getDirectMappedCategoriesForTags,
    isTechOnlyEvent,
    getEffectiveMappedCategories,
    isExcludedFromActiveMap,
    eventMatchesTags,
  };
});
