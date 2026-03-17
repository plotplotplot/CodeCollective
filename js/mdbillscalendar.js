// Store all events globally
let allEvents = [];
let filteredEvents = [];
let rawEvents = [];
let eventGroups = new Set();
let calendar;
let currentView = 'dayGridMonth';
let isMobile = false;
let forceCardView = false;
let activeCategorySlugs = new Set();
let activeSponsorNames = new Set();
let calendarDisplayEvents = [];
let hoverCard = null;
let hoverSwapTimer = null;
let hoverState = null;
let sponsorDirectory = [];
let availableCategoryLabels = [];
let availableSponsors = [];
let sponsorFilterInput = null;
let categoryFilterInput = null;
let billFilterInput = null;
let sponsorTableBody = null;
let categoryTableBody = null;
let billsTableBody = null;
let billFilterCount = null;
let resetFiltersButton = null;
let hideFiltersButton = null;
let billSearchQuery = '';
let billHearingsByNumber = new Map();
const FEATURED_SOURCE_URL = 'https://luma.com/codecollective';
const MGA_SESSION_SLUG = '2026RS';
const DATA_URL = 'https://mgaleg.maryland.gov/2026rs/misc/billsmasterlist/legislation.json';
const LOCAL_DATA_URL = '/data/maryland_bills_2026.json';
const HEARINGS_DATA_URL = '/data/maryland_bill_hearings_2026.json';
const SPONSOR_DIRECTORY_URL = '/data/mga_sponsors_2026.json';
const DATA_SOURCES = [
  {
    label: 'local-cache',
    url: LOCAL_DATA_URL
  },
  {
    label: 'corsproxy',
    url: `https://corsproxy.io/?${encodeURIComponent(DATA_URL)}`
  }
];

const LEGEND_PREFS_KEY = 'calendarLegendPrefs';

// Utility helpers ---------------------------------------------------------
function getTodayStart() {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return today;
}

// Compare only the calendar date so events stay visible all day
function isEventOnOrAfterToday(dateInput, todayStart = getTodayStart()) {
  if (!dateInput) return false;

  const eventDate = new Date(dateInput);
  if (isNaN(eventDate)) return false;

  eventDate.setHours(0, 0, 0, 0);
  return eventDate >= todayStart;
}

// Check if device is mobile
function isMobileDevice() {
  return window.matchMedia('(max-width: 768px)').matches;
  //return false;
}

function slugifyTag(tag) {
  return String(tag || '')
    .toLowerCase()
    .replace(/&/g, 'and')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

function normalizeSourceUrl(url) {
  return String(url || '')
    .trim()
    .toLowerCase()
    .replace(/\/+$/, '');
}

function isFeaturedSource(url) {
  return normalizeSourceUrl(url) === FEATURED_SOURCE_URL;
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function formatMgaHearingDate(value) {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const year = String(date.getFullYear());
  return `${month}/${day}/${year}`;
}

function getBillDetailsUrl(billNumber) {
  const normalized = String(billNumber || '').trim();
  return normalized
    ? `https://mgaleg.maryland.gov/mgawebsite/Legislation/Details/${normalized.toLowerCase()}?ys=${encodeURIComponent(MGA_SESSION_SLUG)}`
    : 'https://mgaleg.maryland.gov/mgawebsite/Legislation/Search';
}

function getBillHearingPageUrl(billNumber) {
  const normalized = String(billNumber || '').trim().toUpperCase();
  return normalized
    ? `https://mgaleg.maryland.gov/mgawebsite/Meetings/Day/${encodeURIComponent(normalized)}`
    : 'https://mgaleg.maryland.gov/mgawebsite/Meetings';
}

function getBillHearingRecord(billNumber) {
  const normalized = String(billNumber || '').trim().toUpperCase();
  return normalized ? (billHearingsByNumber.get(normalized) || null) : null;
}

function pickHearingEntryForEvent(billNumber, hearingValue) {
  const hearingRecord = getBillHearingRecord(billNumber);
  const hearings = Array.isArray(hearingRecord?.hearings) ? hearingRecord.hearings : [];
  if (!hearings.length) {
    return null;
  }

  const targetDate = formatMgaHearingDate(hearingValue);
  const sameDateHearings = hearings.filter((hearing) => String(hearing?.hearing_date || '') === targetDate);
  if (sameDateHearings.length) {
    return sameDateHearings.find((hearing) => hearing?.witness_signup_url) || sameDateHearings[0];
  }

  return hearings.find((hearing) => hearing?.witness_signup_url) || hearings[0];
}

function buildHearingDayPostData(hearingDate) {
  if (!hearingDate) return null;
  return {
    action: 'https://mgaleg.maryland.gov/mgawebsite/Meetings/RefreshDay',
    fields: {
      ys: MGA_SESSION_SLUG.toLowerCase(),
      cmte: 'allcommittees',
      includeBudget: 'show',
      showUpdates: 'show',
      Years: MGA_SESSION_SLUG.slice(0, 4),
      dateType: 'day',
      hearingDateDay: hearingDate
    }
  };
}

function submitPostNavigation(action, fields, target = '_self') {
  if (!action || !fields || typeof document === 'undefined') return;

  const form = document.createElement('form');
  form.method = 'post';
  form.action = action;
  form.target = target;
  form.style.display = 'none';

  Object.entries(fields).forEach(([name, value]) => {
    const input = document.createElement('input');
    input.type = 'hidden';
    input.name = name;
    input.value = String(value ?? '');
    form.appendChild(input);
  });

  document.body.appendChild(form);
  form.submit();
  document.body.removeChild(form);
}

function openBillEventDestination(eventLike, newTab = true) {
  const ext = eventLike?.extendedProps || {};
  const postData = ext.hearingDayPostData;
  if (postData?.action && postData?.fields) {
    submitPostNavigation(postData.action, postData.fields, newTab ? '_blank' : '_self');
    return;
  }

  const fallbackUrl = eventLike?.url || ext.billHearingUrl || ext.billDetailsUrl || '';
  if (!fallbackUrl) return;

  if (newTab) {
    window.open(fallbackUrl, '_blank', 'noopener');
  } else {
    window.location.href = fallbackUrl;
  }
}

function summarizeSubjects(subjects) {
  return (subjects || []).map(subject => subject.Name).filter(Boolean);
}

function extractBillCategories(bill) {
  const names = [
    ...summarizeSubjects(bill.BroadSubjects),
    ...summarizeSubjects(bill.NarrowSubjects)
  ];
  return [...new Set(names.map(name => String(name || '').trim()).filter(Boolean))];
}

function applyTagClasses(element, tags) {
  if (!element || !Array.isArray(tags) || tags.length === 0) return;

  element.classList.add('tagged');
  tags.forEach(tag => {
    const slug = slugifyTag(tag);
    if (slug) {
      element.classList.add(`tag-${slug}`);
    }
  });
}

function getLegendPrefs(categories, sponsors) {
  const defaultCategories = Array.isArray(categories) ? categories.map(slugifyTag).filter(Boolean) : [];
  const defaultSponsors = Array.isArray(sponsors) ? sponsors.filter(Boolean) : [];
  return {
    hidden: true,
    useTagColors: true,
    selectedCategories: defaultCategories,
    selectedSponsors: defaultSponsors
  };
}

function saveLegendPrefs() {
  // Intentionally no-op: filter popup state should not persist.
}

function buildLegend(categories, sponsors) {
  const prefs = getLegendPrefs(categories, sponsors);
  activeCategorySlugs = new Set(prefs.selectedCategories);
  activeSponsorNames = new Set(prefs.selectedSponsors);

  const legendTitle = document.querySelector('.calendar-legend .legend-title');
  if (legendTitle) {
    legendTitle.textContent = 'Filter Maryland bills:';
  }

  const legendItems = document.getElementById('calendar-legend-items');
  if (!legendItems || !Array.isArray(categories) || !Array.isArray(sponsors)) {
    setTagFormattingEnabled(prefs.useTagColors);
    setLegendVisibility(prefs.hidden, { save: false });
    return;
  }

  legendItems.innerHTML = '';

  const controls = document.createElement('div');
  controls.className = 'legend-controls';
  controls.innerHTML = `
    <label class="legend-item legend-toggle">
      <input type="checkbox" id="toggle-tag-formatting" ${prefs.useTagColors ? 'checked' : ''} />
      <span class="legend-text">Use category colors</span>
    </label>
    <div class="legend-actions">
      <button type="button" class="legend-action" data-action="all" data-scope="categories">All categories</button>
      <button type="button" class="legend-action" data-action="none" data-scope="categories">No categories</button>
      <button type="button" class="legend-action" data-action="all" data-scope="sponsors">All sponsors</button>
      <button type="button" class="legend-action" data-action="none" data-scope="sponsors">No sponsors</button>
      <button type="button" class="legend-action" data-action="hide">Hide legend</button>
    </div>
  `;
  legendItems.appendChild(controls);

  const categoriesHeader = document.createElement('div');
  categoriesHeader.className = 'legend-text';
  categoriesHeader.style.fontWeight = '700';
  categoriesHeader.textContent = 'Categories';
  legendItems.appendChild(categoriesHeader);

  const categoriesList = document.createElement('div');
  categoriesList.className = 'legend-list';
  categories.forEach(label => {
    const slug = slugifyTag(label);
    const isChecked = activeCategorySlugs.has(slug);
    const item = document.createElement('label');
    item.className = 'legend-item';
    item.innerHTML = `
      <input type="checkbox" data-filter-type="category" data-filter-value="${escapeHtml(slug)}" ${isChecked ? 'checked' : ''} />
      <span class="legend-swatch tag-${escapeHtml(slug)}"></span>
      <span class="legend-text">${escapeHtml(label)}</span>
    `;
    categoriesList.appendChild(item);
  });
  legendItems.appendChild(categoriesList);

  const sponsorsHeader = document.createElement('div');
  sponsorsHeader.className = 'legend-text';
  sponsorsHeader.style.fontWeight = '700';
  sponsorsHeader.style.marginTop = '10px';
  sponsorsHeader.textContent = 'Sponsors';
  legendItems.appendChild(sponsorsHeader);

  const sponsorsList = document.createElement('div');
  sponsorsList.className = 'legend-list';
  sponsors.forEach(sponsor => {
    const isChecked = activeSponsorNames.has(sponsor);
    const item = document.createElement('label');
    item.className = 'legend-item';
    item.innerHTML = `
      <input type="checkbox" data-filter-type="sponsor" data-filter-value="${escapeHtml(sponsor)}" ${isChecked ? 'checked' : ''} />
      <span class="legend-text">${escapeHtml(sponsor)}</span>
    `;
    sponsorsList.appendChild(item);
  });
  legendItems.appendChild(sponsorsList);

  legendItems.addEventListener('change', event => {
    if (event.target.matches('#toggle-tag-formatting')) {
      setTagFormattingEnabled(event.target.checked);
      saveLegendPrefs();
      return;
    }
    if (!event.target.matches('input[type="checkbox"][data-filter-type]')) return;
    updateActiveFiltersFromLegend();
    applyTagFilters();
  });

  legendItems.addEventListener('click', event => {
    const actionBtn = event.target.closest('.legend-action');
    if (!actionBtn) return;
    const action = actionBtn.dataset.action;
    const scope = actionBtn.dataset.scope || '';
    if (action === 'all' || action === 'none') {
      setLegendCheckboxes(scope, action === 'all');
      return;
    }
    if (action === 'hide') {
      setLegendVisibility(true);
    }
  });

  const visibilityToggle = document.getElementById('legend-visibility-toggle');
  if (visibilityToggle) {
    visibilityToggle.addEventListener('click', () => {
      setLegendVisibility(false);
    });
  }

  setTagFormattingEnabled(prefs.useTagColors);
  setLegendVisibility(prefs.hidden, { save: false });
}

function setTagFormattingEnabled(enabled) {
  document.body.classList.toggle('tags-disabled', !enabled);
}

function setLegendVisibility(hidden, options = {}) {
  document.body.classList.toggle('legend-hidden', hidden);
  const toggleButton = document.getElementById('legend-visibility-toggle');
  if (toggleButton) {
    toggleButton.textContent = hidden ? 'Show legend' : 'Hide legend';
    toggleButton.setAttribute('aria-expanded', hidden ? 'false' : 'true');
  }
  if (options.save !== false) {
    saveLegendPrefs();
  }
}

function setLegendCheckboxes(scope, checked) {
  const selector = scope
    ? `#calendar-legend-items input[type="checkbox"][data-filter-type="${scope.slice(0, -1)}"]`
    : '#calendar-legend-items input[type="checkbox"][data-filter-type]';
  const inputs = document.querySelectorAll(selector);
  inputs.forEach(input => {
    input.checked = checked;
  });
  updateActiveFiltersFromLegend();
  applyTagFilters();
}

function updateActiveFiltersFromLegend() {
  const categoryInputs = document.querySelectorAll('#calendar-legend-items input[type="checkbox"][data-filter-type="category"]');
  activeCategorySlugs = new Set(
    Array.from(categoryInputs)
      .filter(input => input.checked)
      .map(input => input.dataset.filterValue)
  );

  const sponsorInputs = document.querySelectorAll('#calendar-legend-items input[type="checkbox"][data-filter-type="sponsor"]');
  activeSponsorNames = new Set(
    Array.from(sponsorInputs)
      .filter(input => input.checked)
      .map(input => input.dataset.filterValue)
  );
}

function eventMatchesSelections(event) {
  if (!activeCategorySlugs || !activeSponsorNames) return false;

  const categories = Array.isArray(event.extendedProps?.categories) ? event.extendedProps.categories : [];
  const categorySlugs = categories.map(slugifyTag).filter(Boolean);
  const sponsor = String(event.extendedProps?.sponsor || '').trim();
  const searchableText = [
    event.title,
    event.extendedProps?.status,
    event.extendedProps?.hearingType,
    sponsor,
    ...categories
  ].filter(Boolean).join(' ').toLowerCase();

  const categoryMatch = activeCategorySlugs.size === 0 || categorySlugs.some(slug => activeCategorySlugs.has(slug));
  const sponsorMatch = activeSponsorNames.size === 0 || activeSponsorNames.has(sponsor);
  const queryMatch = !billSearchQuery || searchableText.includes(billSearchQuery);
  return categoryMatch && sponsorMatch && queryMatch;
}

function filterEventsBySelections(events) {
  return events.filter(event => eventMatchesSelections(event));
}

function filterRawEventsBySelections(events) {
  return events.filter(event => {
    const extractedCategories = extractBillCategories(event);
    const categories = extractedCategories.length ? extractedCategories : ['Uncategorized'];
    const categorySlugs = categories.map(slugifyTag).filter(Boolean);
    const sponsor = String(event.SponsorPrimary || '').trim() || 'Unknown sponsor';
    const searchableText = [
      event.BillNumber,
      event.Title,
      event.Status,
      sponsor,
      ...categories
    ].filter(Boolean).join(' ').toLowerCase();
    const categoryMatch = activeCategorySlugs.size === 0 || categorySlugs.some(slug => activeCategorySlugs.has(slug));
    const sponsorMatch = activeSponsorNames.size === 0 || activeSponsorNames.has(sponsor);
    const queryMatch = !billSearchQuery || searchableText.includes(billSearchQuery);
    return categoryMatch && sponsorMatch && queryMatch;
  });
}

function applyTagFilters() {
  const filteredLegendEvents = filterEventsBySelections(allEvents);
  calendarDisplayEvents = filteredLegendEvents;

  if (isMobile) {
    initializeMobileCards(filteredLegendEvents);
  } else if (calendar) {
    calendar.removeAllEvents();
    calendar.addEventSource(filteredLegendEvents);
    calendar.render();
  } else {
    initializeCalendar(filteredLegendEvents);
  }

  populateCodeCollectiveEvents(filterRawEventsBySelections(rawEvents));
  renderFilterColumns(filteredLegendEvents);
  saveLegendPrefs();
}

function getAvailableCategoriesAndSponsors(events) {
  const categories = new Set();
  const sponsors = new Set();
  for (const event of events) {
    const eventCategories = Array.isArray(event.extendedProps?.categories) ? event.extendedProps.categories : [];
    for (const category of eventCategories) {
      const clean = String(category || '').trim();
      if (clean) categories.add(clean);
    }
    const sponsor = String(event.extendedProps?.sponsor || '').trim();
    if (sponsor) sponsors.add(sponsor);
  }
  return {
    categories: Array.from(categories).sort((a, b) => a.localeCompare(b)),
    sponsors: Array.from(sponsors).sort((a, b) => a.localeCompare(b))
  };
}

function getSingleSelectedSponsor() {
  return activeSponsorNames.size ? Array.from(activeSponsorNames)[0] : '';
}

function getSingleSelectedCategorySlug() {
  return activeCategorySlugs.size ? Array.from(activeCategorySlugs)[0] : '';
}

function getEventsForSponsorColumn() {
  const selectedCategory = getSingleSelectedCategorySlug();
  return allEvents.filter(event => {
    const categories = Array.isArray(event.extendedProps?.categories) ? event.extendedProps.categories : [];
    const categorySlugs = categories.map(slugifyTag).filter(Boolean);
    const searchableText = [
      event.title,
      event.extendedProps?.status,
      event.extendedProps?.hearingType,
      event.extendedProps?.sponsor,
      ...categories
    ].filter(Boolean).join(' ').toLowerCase();
    const categoryMatch = !selectedCategory || categorySlugs.includes(selectedCategory);
    const queryMatch = !billSearchQuery || searchableText.includes(billSearchQuery);
    return categoryMatch && queryMatch;
  });
}

function getEventsForCategoryColumn() {
  const selectedSponsor = getSingleSelectedSponsor();
  return allEvents.filter(event => {
    const sponsor = String(event.extendedProps?.sponsor || '').trim();
    const categories = Array.isArray(event.extendedProps?.categories) ? event.extendedProps.categories : [];
    const searchableText = [
      event.title,
      event.extendedProps?.status,
      event.extendedProps?.hearingType,
      sponsor,
      ...categories
    ].filter(Boolean).join(' ').toLowerCase();
    const sponsorMatch = !selectedSponsor || sponsor === selectedSponsor;
    const queryMatch = !billSearchQuery || searchableText.includes(billSearchQuery);
    return sponsorMatch && queryMatch;
  });
}

function renderSponsorTable() {
  if (!sponsorTableBody) return;
  const sponsorQuery = (sponsorFilterInput?.value || '').trim().toLowerCase();
  const selectedSponsor = getSingleSelectedSponsor();
  const sponsorCounts = new Map();
  for (const event of getEventsForSponsorColumn()) {
    const sponsor = String(event.extendedProps?.sponsor || 'Unknown sponsor').trim() || 'Unknown sponsor';
    sponsorCounts.set(sponsor, (sponsorCounts.get(sponsor) || 0) + 1);
  }

  const rows = [...sponsorCounts.entries()]
    .filter(([sponsor]) => !sponsorQuery || sponsor.toLowerCase().includes(sponsorQuery))
    .sort((a, b) => (b[1] - a[1]) || a[0].localeCompare(b[0]))
    .map(([sponsor, count]) => `
      <div class="list-row">
        <button type="button" class="sponsor-button${sponsor === selectedSponsor ? ' active' : ''}" data-sponsor="${escapeHtml(sponsor)}">
          ${escapeHtml(sponsor)}
        </button>
        <span class="list-count">${count.toLocaleString()}</span>
      </div>
    `)
    .join('');

  sponsorTableBody.innerHTML = rows || '<div class="list-row"><span>No sponsor matches.</span><span class="list-count">0</span></div>';
}

function renderCategoryTable() {
  if (!categoryTableBody) return;
  const categoryQuery = (categoryFilterInput?.value || '').trim().toLowerCase();
  const selectedCategory = getSingleSelectedCategorySlug();
  const categoryCounts = new Map();
  for (const event of getEventsForCategoryColumn()) {
    const categories = Array.isArray(event.extendedProps?.categories) ? event.extendedProps.categories : ['Uncategorized'];
    for (const category of categories) {
      const label = String(category || '').trim() || 'Uncategorized';
      categoryCounts.set(label, (categoryCounts.get(label) || 0) + 1);
    }
  }

  const rows = [...categoryCounts.entries()]
    .filter(([category]) => !categoryQuery || category.toLowerCase().includes(categoryQuery))
    .sort((a, b) => (b[1] - a[1]) || a[0].localeCompare(b[0]))
    .map(([category, count]) => {
      const slug = slugifyTag(category);
      return `
        <div class="list-row">
          <button type="button" class="sponsor-button${slug === selectedCategory ? ' active' : ''}" data-category="${escapeHtml(slug)}">
            ${escapeHtml(category)}
          </button>
          <span class="list-count">${count.toLocaleString()}</span>
        </div>
      `;
    })
    .join('');

  categoryTableBody.innerHTML = rows || '<div class="list-row"><span>No category matches.</span><span class="list-count">0</span></div>';
}

function renderBillsTable(events) {
  if (!billsTableBody) return;
  const rows = [...events]
    .sort((a, b) => new Date(a.start) - new Date(b.start))
    .slice(0, 500)
    .map(event => `
      <div class="list-row">
        <button type="button" class="sponsor-button" data-event-id="${escapeHtml(String(event.id || ''))}">
          ${escapeHtml(event.title || 'Untitled Bill')}
        </button>
        <span class="list-count">${escapeHtml(formatEventDate(event.start, event.end))}</span>
      </div>
    `)
    .join('');
  billsTableBody.innerHTML = rows || '<div class="list-row"><span>No hearings match those filters.</span><span class="list-count">0</span></div>';
}

function renderFilterColumns(events) {
  renderSponsorTable();
  renderCategoryTable();
  renderBillsTable(events);
  if (billFilterCount) {
    billFilterCount.textContent = `${events.length.toLocaleString()} hearings shown`;
  }
}

function initializeFilterColumns() {
  sponsorFilterInput = document.getElementById('sponsor-filter');
  categoryFilterInput = document.getElementById('category-filter');
  billFilterInput = document.getElementById('bill-filter');
  sponsorTableBody = document.getElementById('sponsor-table-body');
  categoryTableBody = document.getElementById('category-table-body');
  billsTableBody = document.getElementById('bills-table-body');
  billFilterCount = document.getElementById('bill-filter-count');
  resetFiltersButton = document.getElementById('reset-filters');
  hideFiltersButton = document.getElementById('hide-filters');

  sponsorFilterInput?.addEventListener('input', renderSponsorTable);
  categoryFilterInput?.addEventListener('input', renderCategoryTable);
  billFilterInput?.addEventListener('input', () => {
    billSearchQuery = String(billFilterInput.value || '').trim().toLowerCase();
    applyTagFilters();
  });

  sponsorTableBody?.addEventListener('click', event => {
    const button = event.target.closest('.sponsor-button[data-sponsor]');
    if (!button) return;
    const sponsor = String(button.dataset.sponsor || '').trim();
    const current = getSingleSelectedSponsor();
    activeSponsorNames = (current === sponsor || !sponsor) ? new Set() : new Set([sponsor]);
    applyTagFilters();
  });

  categoryTableBody?.addEventListener('click', event => {
    const button = event.target.closest('.sponsor-button[data-category]');
    if (!button) return;
    const category = String(button.dataset.category || '').trim();
    const current = getSingleSelectedCategorySlug();
    activeCategorySlugs = (current === category || !category) ? new Set() : new Set([category]);
    applyTagFilters();
  });

  billsTableBody?.addEventListener('click', event => {
    const button = event.target.closest('.sponsor-button[data-event-id]');
    if (!button || !calendar) return;
    const eventId = String(button.dataset.eventId || '');
    const matched = calendar.getEventById(eventId);
    if (matched?.start) {
      calendar.gotoDate(matched.start);
    }
  });

  resetFiltersButton?.addEventListener('click', () => {
    activeSponsorNames = new Set();
    activeCategorySlugs = new Set();
    billSearchQuery = '';
    if (sponsorFilterInput) sponsorFilterInput.value = '';
    if (categoryFilterInput) categoryFilterInput.value = '';
    if (billFilterInput) billFilterInput.value = '';
    applyTagFilters();
  });

  hideFiltersButton?.addEventListener('click', () => {
    setLegendVisibility(true);
  });

  document.getElementById('legend-visibility-toggle')?.addEventListener('click', () => {
    setLegendVisibility(false);
  });
}

function normalizePersonName(value) {
  return String(value || '')
    .toLowerCase()
    .replace(/\b(senator|delegate)\b/g, '')
    .replace(/[^a-z0-9,\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function expandNameCandidates(name) {
  const clean = normalizePersonName(name);
  if (!clean) {
    return [];
  }
  const out = new Set([clean]);
  if (clean.includes(',')) {
    const [last, first] = clean.split(',').map(part => part.trim()).filter(Boolean);
    if (first && last) {
      out.add(`${first} ${last}`.trim());
    }
  }
  return [...out];
}

function findDirectoryRecordBySponsorName(sponsorName) {
  if (!sponsorDirectory.length) {
    return null;
  }
  const targets = expandNameCandidates(sponsorName);
  if (!targets.length) {
    return null;
  }

  for (const rec of sponsorDirectory) {
    const heading = normalizePersonName(rec.name_heading || '');
    const slug = normalizePersonName(String(rec.slug || '').replace(/[0-9]+$/g, ''));
    if (targets.includes(heading) || targets.includes(slug)) {
      return rec;
    }
  }

  const targetLast = targets[0].split(' ').filter(Boolean).at(-1);
  if (!targetLast) {
    return null;
  }
  const matches = sponsorDirectory.filter(rec => {
    const headingTokens = normalizePersonName(rec.name_heading || '').split(' ').filter(Boolean);
    return headingTokens.at(-1) === targetLast;
  });
  return matches.length === 1 ? matches[0] : null;
}

function getImageSource(imageRecord) {
  if (!imageRecord) {
    return '';
  }
  if (imageRecord.path) {
    return String(imageRecord.path);
  }
  if (imageRecord.base64 && imageRecord.mime_type) {
    return `data:${imageRecord.mime_type};base64,${imageRecord.base64}`;
  }
  return '';
}

function buildSponsorImageMarkup(sponsorName, directoryRecord) {
  if (!directoryRecord) {
    return '';
  }
  const portraitSrc = getImageSource(directoryRecord.portrait_image);
  const standardizedSrc = getImageSource(directoryRecord.standardized_district_map_image);
  if (standardizedSrc) {
    return `
      <section class="hover-card-images sponsor-hover-media">
        <figure class="hover-map-figure">
          <img class="hover-map-image" alt="Standardized Maryland district map for ${escapeHtml(sponsorName)}" src="${escapeHtml(standardizedSrc)}">
          <figcaption>Maryland District Context Map</figcaption>
        </figure>
        ${portraitSrc ? `
          <figure class="hover-portrait-overlay">
            <img class="hover-portrait-image" alt="Sponsor portrait for ${escapeHtml(sponsorName)}" src="${escapeHtml(portraitSrc)}">
          </figure>
        ` : ''}
      </section>
    `;
  }
  if (portraitSrc) {
    return `
      <section class="hover-card-images sponsor-hover-media">
        <figure class="hover-map-figure">
          <img class="hover-map-image" alt="Sponsor portrait for ${escapeHtml(sponsorName)}" src="${escapeHtml(portraitSrc)}">
          <figcaption>Portrait</figcaption>
        </figure>
      </section>
    `;
  }
  return '';
}
// Generic image prefetching function (with unique URLs only)
function prefetchImages(urls) {
  if (!window.Promise || !window.fetch) return; // Skip if browser doesn't support

  const uniqueUrls = Array.from(new Set(urls)); // Remove duplicates

  uniqueUrls.forEach(url => {
    // Create link preload for important above-the-fold images
    const link = document.createElement('link');
    link.rel = 'preload';
    link.as = 'image';
    link.href = url;
    document.head.appendChild(link);

    // Fetch all images to cache them
    fetch(url, {
      mode: 'no-cors',
      cache: 'force-cache'
    }).catch(() => { }); // Silent fail is okay for prefetch
  });
}


function getCityOptions() {
  return window.CALENDAR_CITY_OPTIONS || ['baltimore', 'westvirginia', 'hawaii', 'dc'];
}

// Function to get city from URL parameters
function getCityFromUrl() {
  const urlParams = new URLSearchParams(window.location.search);
  const city = urlParams.get('city');
  const cityOptions = getCityOptions();
  return cityOptions.includes(city) ? city : 'baltimore'; // Default to baltimore if no city specified
}

function shouldStayOnCalendarView() {
  const urlParams = new URLSearchParams(window.location.search);
  const viewPreference = (urlParams.get('view') || '').toLowerCase();

  if (viewPreference === 'calendar' || viewPreference === 'desktop') {
    sessionStorage.setItem('preferCalendarView', '1');
    return true;
  }

  return sessionStorage.getItem('preferCalendarView') === '1';
}

function prefetchBillsDataCache() {
  fetch(LOCAL_DATA_URL, { cache: 'force-cache' }).catch(() => { });
}

async function fetchBillsData() {
  const errors = [];

  for (const source of DATA_SOURCES) {
    try {
      const response = await fetch(source.url, { cache: 'force-cache' });
      if (!response.ok) {
        throw new Error(`status ${response.status}`);
      }

      const text = await response.text();
      const parsed = JSON.parse(text);
      if (!Array.isArray(parsed)) {
        throw new Error('unexpected payload shape');
      }

      return { bills: parsed, source: source.label };
    } catch (error) {
      errors.push(`${source.label}: ${error.message}`);
    }
  }

  throw new Error(errors.join(' | '));
}

async function fetchSponsorDirectory() {
  try {
    const response = await fetch(SPONSOR_DIRECTORY_URL, { cache: 'force-cache' });
    if (!response.ok) {
      return [];
    }
    const payload = await response.json();
    return Array.isArray(payload.records) ? payload.records : [];
  } catch (error) {
    return [];
  }
}

async function fetchHearingsData() {
  try {
    const response = await fetch(HEARINGS_DATA_URL, { cache: 'force-cache' });
    if (!response.ok) {
      return new Map();
    }
    const payload = await response.json();
    const records = payload && typeof payload === 'object' ? payload.records : null;
    return new Map(Object.entries(records || {}));
  } catch (error) {
    return new Map();
  }
}

// Fetch and parse event data
document.addEventListener('DOMContentLoaded', function () {
  hoverCard = document.getElementById('hover-card');
  forceCardView = Boolean(window.FORCE_CALENDAR_CARDS);
  const stayOnCalendar = shouldStayOnCalendarView();
  const mobileViewport = isMobileDevice();
  isMobile = forceCardView ? true : (mobileViewport && !stayOnCalendar);
  prefetchBillsDataCache();

  Promise.all([fetchBillsData(), fetchSponsorDirectory(), fetchHearingsData()])
    .then(([{ bills, source }, directory, hearingMap]) => {
      sponsorDirectory = directory;
      billHearingsByNumber = hearingMap;
      rawEvents = Array.isArray(bills) ? bills : [];
      allEvents = processEvents(rawEvents);
      const available = getAvailableCategoriesAndSponsors(allEvents);
      availableCategoryLabels = available.categories;
      availableSponsors = available.sponsors;

      // Extract all unique event image URLs
      const eventImageUrls = allEvents
        .map(event => event.extendedProps?.imageUrl)
        .filter(url => url); // Remove null/undefined

      // Prefetch all event images in parallel
      prefetchImages(eventImageUrls);

      filteredEvents = [...allEvents]; // Make a copy for filtering

      initializeFilterColumns();
      setLegendVisibility(true, { save: false });
      applyTagFilters();

      setupViewSelectors();
      document.getElementById('loading').style.display = 'none';

      if (!isMobile) {
        highlightToday();
      }

      if (source === 'corsproxy') {
        console.warn('Loaded Maryland bills via fallback proxy.');
      }
    })
    .catch(error => {
      console.error('Error loading Maryland bills:', error);
      document.getElementById('loading').innerHTML = '<i class="fas fa-exclamation-circle"></i> Error loading Maryland bills. Please try again.';
    });

  // Add CSS for today's date styling (desktop only)
  if (!isMobile) {
    addTodayStyles();
  }

  if (!forceCardView) {
    // Debounce the resize event listener to avoid excessive re-rendering
    let resizeTimeout;
    window.addEventListener('resize', function () {
      clearTimeout(resizeTimeout);
      resizeTimeout = setTimeout(() => {
        const wasMobile = isMobile;
        const mobileResizeViewport = isMobileDevice();
        isMobile = forceCardView ? true : (mobileResizeViewport && !shouldStayOnCalendarView());

        if (wasMobile !== isMobile) {
          if (isMobile) {
            destroyCalendar();
            applyTagFilters();
          } else {
            destroyMobileCards();
            const calendarEl = document.getElementById('calendar');
            if (calendarEl) {
              calendarEl.style.display = '';
            }
            applyTagFilters();
            addTodayStyles();
          }
        }
      }, 200); // Adjust debounce time as needed
    });
  }
});

// Initialize mobile card view
function initializeMobileCards(events) {
  const container = document.getElementById('calendar');
  if (!container) return;

  container.style.display = '';
  container.innerHTML = '';
  container.className = 'mobile-cards-container';

  // Filter events to only show future events (after today)
  const todayStart = getTodayStart();

  const futureEvents = events.filter(event =>
    isEventOnOrAfterToday(event.start, todayStart)
  );

  // Sort events by date and time
  futureEvents.sort((a, b) => new Date(a.start) - new Date(b.start));

  // Create individual cards for each event
  futureEvents.forEach(event => {
    const eventCard = createEventCard(event);
    container.appendChild(eventCard);
  });

  // If no future events, show a message
  if (futureEvents.length === 0) {
    const noEventsMsg = document.createElement('div');
    noEventsMsg.className = 'no-events-message';
    noEventsMsg.innerHTML = `
      <i class="fas fa-calendar-times"></i>
      <h3>No upcoming events</h3>
      <p>Check back later for new events!</p>
    `;
    container.appendChild(noEventsMsg);
  }
}

// Create individual event card with expandable description
function toggleCardDescription(button) {
  const card = button.closest('.card-content');
  const shortDesc = card.querySelector('.card-description-short');
  const fullDesc = card.querySelector('.card-description-full');
  const moreBtn = card.querySelector('.more-btn');

  if (fullDesc.style.display === 'none' || !fullDesc.style.display) {
    // Show full description
    shortDesc.style.display = 'none';
    fullDesc.style.display = 'block';
    moreBtn.innerHTML = '<i class="fas fa-chevron-up"></i> Less';
  } else {
    // Show short description
    shortDesc.style.display = 'block';
    fullDesc.style.display = 'none';
    moreBtn.innerHTML = '<i class="fas fa-chevron-down"></i> More';
  }
}
// Create individual event card
function createEventCard(event) {
  const card = document.createElement('div');
  card.className = 'card-content';

  const startTime = formatEventTime(new Date(event.start));
  const endTime = event.end ? formatEventTime(new Date(event.end)) : '';
  const timeRange = endTime ? `${startTime} - ${endTime}` : startTime;

  // Format the full date
  const eventDate = new Date(event.start);
  const fullDate = eventDate.toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });

  // Prepare description with markdown support
  const rawDescription = event.description || '';
  const description = rawDescription.trim();
  const maxDescLength = 100;
  const needsMore = description.length > maxDescLength;

  // Create short description by stripping markdown and truncating
  const shortDesc = needsMore ?
    stripMarkdown(description).substring(0, maxDescLength) + '...' :
    stripMarkdown(description);

  card.innerHTML = `
    ${event.extendedProps.imageUrl ?
      `<div class="card-image" style="background-image: url(${event.extendedProps.imageUrl})"></div>` :
      '<div class="card-image-placeholder"><i class="fas fa-calendar-alt"></i></div>'
    }
      <h3 class="card-title">${event.title}</h3>
      <div class="card-meta">
        <div class="card-time">
          ${fullDate}, ${timeRange}
        </div>${event.location ? `
  <div class="card-location">
    <i class="fas fa-map-marker-alt"></i> 
    <span class="location-address">
      ${[
        event.location.address
      ].filter(Boolean).join(', ')}
    </span>
  </div>
` : ''}


      </div>
      ${description ? `
        <div class="card-description">
          <div class="card-description-short">${shortDesc}</div>
          <div class="card-description-full markdown-content" style="display: none;"></div>
          ${needsMore ? '<button class="more-btn" onclick="toggleCardDescription(this)"><i class="fas fa-chevron-down"></i> More</button>' : ''}
        </div>
      ` : ''}
  `;

  applyTagClasses(card, event.extendedProps?.tags);
  if (isFeaturedSource(event.extendedProps?.source)) {
    card.classList.add('source-codecollective-luma');
  }

  // Process markdown for full description if needed
  if (description && needsMore) {
    const fullDescContainer = card.querySelector('.card-description-full');
    if (fullDescContainer) {
      if (window.marked && typeof window.marked.parse === 'function') {
        fullDescContainer.innerHTML = marked.parse(description);
      } else {
        fullDescContainer.textContent = description;
      }
    }
  }

  // Add click handler (but not for the more button)
  card.addEventListener('click', function (e) {
    if (e.target.closest('.more-btn') || e.target.closest('a')) {
      return;
    }
    openBillEventDestination(event, true);
  });

  return card;
}

// Helper function to strip markdown for short description
function stripMarkdown(text) {
  return text
    .replace(/^#+\s+/gm, '')          // Remove headings
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')  // Remove links but keep text
    .replace(/\*\*([^*]+)\*\*/g, '$1')        // Remove bold
    .replace(/\*([^*]+)\*/g, '$1')            // Remove italics
    .replace(/`([^`]+)`/g, '$1')              // Remove code
    .replace(/^\s*[-*+]\s+/gm, '')    // Remove list markers
    .replace(/\n+/g, ' ');            // Replace newlines with spaces
}

// Destroy mobile cards view
function destroyMobileCards() {
  const container = document.getElementById('calendar');
  if (!container) return;
  container.innerHTML = '';
  container.className = '';
  container.style.display = '';
}

// Destroy calendar view
function destroyCalendar() {
  if (calendar) {
    calendar.destroy();
    calendar = null;
  }
}

// Add CSS for today's date styling (desktop only)
function addTodayStyles() {
  const style = document.createElement('style');
  style.textContent = `
    .fc .fc-day-today .fc-daygrid-day-number {
      background-color: yellow !important;
      color: black !important;
      font-weight: bold !important;
      padding: 5px;
    }
  `;
  document.head.appendChild(style);
}

// Function to ensure today's date is highlighted correctly (desktop only)
function highlightToday() {
  if (isMobile) return;

  const todayEl = document.querySelector('.fc-day-today .fc-daygrid-day-number');
  if (todayEl) {
    todayEl.style.backgroundColor = 'yellow';
    todayEl.style.color = 'black';
    todayEl.style.fontWeight = 'bold';
  }
}

// Process the JSON event data into FullCalendar format
function processEvents(eventsData) {
  const hearingFields = [
    ['HearingDateTimePrimaryHouseOfOrigin', 'Primary House of Origin Hearing'],
    ['HearingDateTimeSecondaryHouseOfOrigin', 'Secondary House of Origin Hearing'],
    ['HearingDateTimePrimaryOppositeHouse', 'Primary Opposite House Hearing'],
    ['HearingDateTimeSecondaryOppositeHouse', 'Secondary Opposite House Hearing']
  ];

  const calendarEvents = [];
  for (const bill of eventsData) {
    const billNumber = String(bill.BillNumber || '').trim();
    const billId = String(billNumber || `bill-${calendarEvents.length}`).toLowerCase();
    const title = bill.Title || billNumber || 'Untitled Bill';
    const sponsor = bill.SponsorPrimary || 'Unknown sponsor';
    const status = bill.Status || 'Status unavailable';
    const synopsis = String(bill.Synopsis || '').trim();
    const extractedCategories = extractBillCategories(bill);
    const categories = extractedCategories.length ? extractedCategories : ['Uncategorized'];
    const tags = categories;
    const billDetailsUrl = getBillDetailsUrl(billNumber);
    const billHearingUrl = getBillHearingPageUrl(billNumber);

    for (const [fieldName, hearingLabel] of hearingFields) {
      const hearingValue = bill[fieldName];
      if (!hearingValue) {
        continue;
      }

      const hearingDate = new Date(hearingValue);
      if (Number.isNaN(hearingDate.getTime())) {
        continue;
      }

      const hearingEntry = pickHearingEntryForEvent(billNumber, hearingValue);
      const hearingDayPostData = buildHearingDayPostData(
        hearingEntry?.hearing_date || formatMgaHearingDate(hearingValue)
      );
      const witnessSignupUrl = String(hearingEntry?.witness_signup_url || '').trim();
      const destinationUrl = witnessSignupUrl || billHearingUrl || billDetailsUrl;

      eventGroups.add('Maryland Bills');
      calendarEvents.push({
        id: `${billId}-${fieldName}`,
        title: `${billNumber || 'Bill'}: ${title}`,
        start: hearingValue,
        end: hearingValue,
        description: `${hearingLabel}\nSponsor: ${sponsor}\nStatus: ${status}${synopsis ? `\n\n${synopsis}` : ''}`,
        location: {
          address: hearingLabel,
          name: hearingLabel
        },
        url: destinationUrl,
        extendedProps: {
          group: 'Maryland Bills',
          imageUrl: '',
          tags,
          categories,
          source: 'mgaleg',
          billNumber,
          hearingType: hearingLabel,
          sponsor,
          status,
          billDetailsUrl,
          billHearingUrl,
          witnessSignupUrl,
          hearingDayPostData
        },
        backgroundColor: "#0f0f0f0",
        borderColor: "#0f0f0f0",
        textColor: "#000"
      });
    }
  }

  return calendarEvents;
}

function positionHoverCard(clientX, clientY) {
  if (!hoverCard) {
    return;
  }
  const gap = 12;
  const rect = hoverCard.getBoundingClientRect();
  let left = clientX + gap;
  let top = clientY + gap;
  if (left + rect.width > window.innerWidth - 8) {
    left = clientX - rect.width - gap;
  }
  if (top + rect.height > window.innerHeight - 8) {
    top = clientY - rect.height - gap;
  }
  left = Math.max(8, Math.min(left, window.innerWidth - rect.width - 8));
  top = Math.max(8, Math.min(top, window.innerHeight - rect.height - 8));
  hoverCard.style.left = `${left}px`;
  hoverCard.style.top = `${top}px`;
}

function showHoverCard(markup, clientX, clientY) {
  if (!hoverCard) {
    return;
  }
  const nextMarkup = `<div class="hover-card-content">${markup}</div>`;
  if (hoverCard.classList.contains('open') && hoverCard.innerHTML !== nextMarkup) {
    if (hoverSwapTimer) {
      clearTimeout(hoverSwapTimer);
      hoverSwapTimer = null;
    }
    hoverCard.classList.add('is-swapping');
    hoverSwapTimer = window.setTimeout(() => {
      hoverCard.innerHTML = nextMarkup;
      hoverCard.classList.remove('is-swapping');
      hoverSwapTimer = null;
      const isOverlayMode = hoverCard.classList.contains('left-overlay')
        || hoverCard.classList.contains('right-overlay');
      if (!isOverlayMode) {
        positionHoverCard(clientX, clientY);
      }
    }, 80);
  } else {
    hoverCard.innerHTML = nextMarkup;
  }
  hoverCard.classList.remove('left-overlay');
  hoverCard.classList.remove('right-overlay');
  hoverCard.style.height = '';
  hoverCard.style.maxHeight = '';
  hoverCard.classList.add('open');
  hoverCard.setAttribute('aria-hidden', 'false');
  positionHoverCard(clientX, clientY);
}

function positionLeftOverlayCard() {
  if (!hoverCard) {
    return;
  }
  const left = 10;
  const top = 84;
  const height = Math.max(220, window.innerHeight - top - 10);
  hoverCard.style.left = `${left}px`;
  hoverCard.style.top = `${top}px`;
  hoverCard.style.height = `${height}px`;
  hoverCard.style.maxHeight = `${height}px`;
}

function positionRightOverlayCard() {
  if (!hoverCard) {
    return;
  }
  const top = 84;
  const height = Math.max(220, window.innerHeight - top - 10);
  const width = hoverCard.offsetWidth;
  const rightGap = 10;
  const left = Math.max(10, window.innerWidth - width - rightGap);
  hoverCard.style.left = `${left}px`;
  hoverCard.style.top = `${top}px`;
  hoverCard.style.height = `${height}px`;
  hoverCard.style.maxHeight = `${height}px`;
}

function hideHoverCard() {
  if (!hoverCard) {
    return;
  }
  if (hoverSwapTimer) {
    clearTimeout(hoverSwapTimer);
    hoverSwapTimer = null;
  }
  hoverCard.classList.remove('open');
  hoverCard.classList.remove('left-overlay');
  hoverCard.classList.remove('right-overlay');
  hoverCard.classList.remove('is-swapping');
  hoverCard.setAttribute('aria-hidden', 'true');
  hoverCard.innerHTML = '';
  hoverState = null;
}

window.addEventListener('scroll', hideHoverCard, { passive: true });
window.addEventListener('resize', hideHoverCard);

function buildCalendarEventHoverMarkup(event) {
  const ext = event.extendedProps || {};
  const hearingType = ext.hearingType || 'Hearing';
  const sponsor = ext.sponsor || 'Unknown sponsor';
  const status = ext.status || 'Status unavailable';
  const categories = Array.isArray(ext.categories) ? ext.categories : [];
  const start = event.start ? formatEventDate(event.start, event.end) : 'Date unavailable';
  const rawDescription = String(event.description || '').trim();
  const normalizedDescription = rawDescription
    .replace(/\s*\n\s*/g, ' | ')
    .replace(/\s+/g, ' ')
    .trim();
  const directoryRecord = findDirectoryRecordBySponsorName(sponsor);
  const imageMarkup = buildSponsorImageMarkup(sponsor, directoryRecord);

  return `
      <p class="hover-card-kicker">Bill Hearing</p>
      <h3>${escapeHtml(event.title || 'Untitled Bill')}</h3>
      <p class="hover-card-meta">Date: ${escapeHtml(start)}</p>
      <p class="hover-card-meta">Sponsor: ${escapeHtml(sponsor)}</p>
      <p class="hover-card-meta">Status: ${escapeHtml(status)}</p>
      <p class="hover-card-meta hover-card-meta-accent">Type: ${escapeHtml(hearingType)}</p>
      ${categories.length ? `<p class="hover-card-meta">Categories: ${escapeHtml(categories.join(' | '))}</p>` : ''}
      ${normalizedDescription ? `<p>${escapeHtml(normalizedDescription)}</p>` : ''}
      ${imageMarkup}
    `;
}

function showCalendarEventHover(event, clientX, clientY) {
  if (!hoverCard) {
    return;
  }
  hoverState = { type: 'calendar-event', id: event.id || '' };
  showHoverCard(buildCalendarEventHoverMarkup(event), clientX, clientY);

  const cursorOnLeftHalf = clientX < (window.innerWidth / 2);
  if (cursorOnLeftHalf) {
    hoverCard.classList.add('right-overlay');
    positionRightOverlayCard();
  } else {
    hoverCard.classList.add('left-overlay');
    positionLeftOverlayCard();
  }
}

// Format event time to display like "3PM"
function formatEventTime(date) {
  if (!date) return '';

  const hours = date.getHours();
  const minutes = date.getMinutes();

  // Determine AM/PM
  const period = hours >= 12 ? 'PM' : 'AM';

  // Convert to 12-hour format
  const displayHours = hours % 12 || 12; // 0 should be displayed as 12

  // Only show minutes if not on the hour
  const timeString = minutes === 0 ?
    `${displayHours}${period}` :
    `${displayHours}:${minutes.toString().padStart(2, '0')}${period}`;

  return timeString;
}

// Get the latest event with an image for a specific day (desktop only)
function getLatestEventWithImageForDay(events, date) {
  if (isMobile) return null;

  // Format the date to YYYY-MM-DD using local timezone
  const dateStr = date.getFullYear() + '-' +
    String(date.getMonth() + 1).padStart(2, '0') + '-' +
    String(date.getDate()).padStart(2, '0');

  // Filter events that are on this day and have an image
  const dayEvents = events.filter(event => {
    const eventDate = new Date(event.start);
    const eventDateStr = eventDate.getFullYear() + '-' +
      String(eventDate.getMonth() + 1).padStart(2, '0') + '-' +
      String(eventDate.getDate()).padStart(2, '0');
    return eventDateStr === dateStr && event.extendedProps.imageUrl;
  });

  // If no events with images for this day, return null
  if (dayEvents.length === 0) return null;

  // Sort events by start time, descending (latest first)
  dayEvents.sort((a, b) => new Date(b.start) - new Date(a.start));

  // Return the latest event
  return dayEvents[0];
}

// Get a random event with an image for a specific day (desktop only)
function getRandomImageForDay(events, date) {
  if (isMobile) return null;
  
  // Format the date to YYYY-MM-DD using local timezone
  const dateStr = date.getFullYear() + '-' +
    String(date.getMonth() + 1).padStart(2, '0') + '-' +
    String(date.getDate()).padStart(2, '0');
  
  // Filter events that are on this day and have an image
  const dayEvents = events.filter(event => {
    const eventDate = new Date(event.start);
    const eventDateStr = eventDate.getFullYear() + '-' +
      String(eventDate.getMonth() + 1).padStart(2, '0') + '-' +
      String(eventDate.getDate()).padStart(2, '0');
    return eventDateStr === dateStr && event.extendedProps.imageUrl;
  });
  
  // If no events with images for this day, return null
  if (dayEvents.length === 0) return null;
  
  // Return a random event instead of the latest one
  const randomIndex = Math.floor(Math.random() * dayEvents.length);
  return dayEvents[randomIndex];
}

// Initialize the FullCalendar (desktop only)
function initializeCalendar(events) {
  if (isMobile) return;
  calendarDisplayEvents = events;

  // Filter events to show only next 4 weeks starting from today
  const today = getTodayStart();

  const fourWeeksFromNow = new Date(today);
  fourWeeksFromNow.setDate(today.getDate() + 28); // 4 weeks = 28 days
  fourWeeksFromNow.setHours(23, 59, 59, 999); // End of the day

  const filteredEvents = events.filter(event => {
    const eventDate = new Date(event.start);
    if (isNaN(eventDate)) return false;
    return isEventOnOrAfterToday(event.start, today) && eventDate <= fourWeeksFromNow;
  });

  // Calculate the start of current week (Sunday)
  const startOfWeek = new Date(today);
  const dayOfWeek = startOfWeek.getDay(); // 0 = Sunday, 1 = Monday, etc.
  startOfWeek.setDate(startOfWeek.getDate() - dayOfWeek);
  startOfWeek.setHours(0, 0, 0, 0);

  // Calculate end of 4th week (current week + 3 weeks after)
  const endOf4Weeks = new Date(startOfWeek);
  endOf4Weeks.setDate(startOfWeek.getDate() + 29); // 4 weeks + 1 day (since end is exclusive)

  const calendarEl = document.getElementById('calendar');
  calendar = new FullCalendar.Calendar(calendarEl, {
    initialView: 'dayGridFourWeek',
    views: {
      dayGridFourWeek: {
        type: 'dayGrid',
        duration: { weeks: 4 },
        buttonText: '4 Weeks',
        fixedWeekCount: true,     // Always show the same number of weeks (usually 6)
        height: 'auto',           // Let calendar resize to fit, or use a fixed value (e.g., 600)

      },
    },
    headerToolbar: {
      left: 'prev',
      center: 'title',
      right: 'next'
    },
    validRange: {
      start: today             // today's date (inclusive)
    },

    events: events, // Use all events (validRange will filter the display)
    eventClassNames: function (arg) {
      return isFeaturedSource(arg.event.extendedProps?.source) ? ['source-codecollective-luma'] : [];
    },
    eventClick: function (info) {
      info.jsEvent.preventDefault();

      // Allow ctrl/cmd click to open in a new tab
      if (info.jsEvent.ctrlKey || info.jsEvent.metaKey) {
        openBillEventDestination(info.event, true);
      } else {
        openBillEventDestination(info.event, false);
      }
    }
    ,
    eventTimeFormat: {
      hour: 'numeric',
      minute: '2-digit',
      meridiem: 'short'
    },
    height: 'auto',
    dayMaxEvents: true, // Allow "more" link when too many events
    dayCellDidMount: function (info) {
      // Only show images for today and future dates
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const cellDate = new Date(info.date);
      cellDate.setHours(0, 0, 0, 0);

      // Skip if this day is before today
      if (cellDate < today) {
        return;
      }

      // Get the latest event with an image for this day
      const latestEvent = getRandomImageForDay(calendarDisplayEvents, info.date);

      if (latestEvent && latestEvent.extendedProps.imageUrl) {
        // Get the day cell element
        const cellEl = info.el;

        // Find the day frame element (this is the actual "day" content area)
        const dayFrame = cellEl.querySelector('.fc-daygrid-day-frame');

        if (dayFrame) {
          // Add a class to help with styling
          dayFrame.classList.add('has-event-background');

          // Create a semi-transparent background with the event image
          const bgDiv = document.createElement('div');
          bgDiv.classList.add('fc-day-background');
          bgDiv.style.backgroundImage = `url(${latestEvent.extendedProps.imageUrl})`;
          bgDiv.style.backgroundSize = 'cover';
          bgDiv.style.backgroundPosition = 'center';
          bgDiv.style.backgroundRepeat = 'no-repeat';

          // Add the background div as the first child of the day frame
          dayFrame.style.position = 'relative'; // Ensure positioning context
          dayFrame.prepend(bgDiv);

          // Make sure event content is above the background
          const eventContent = dayFrame.querySelector('.fc-daygrid-day-events');
          if (eventContent) {
            eventContent.style.position = 'relative';
            eventContent.style.zIndex = '2';
          }
        }
      }
    },
    eventContent: function (info) {
      // Handle list view separately
      if (info.view.type.includes('list')) {
        return; // Use default list view rendering
      }

      const eventEl = document.createElement('div');
      eventEl.classList.add('fc-event-content-wrapper');

      // Format the time
      const eventTime = formatEventTime(info.event.start);

      // Add title with time
      const titleEl = document.createElement('div');
      titleEl.classList.add('fc-event-title');
      if (isFeaturedSource(info.event.extendedProps?.source)) {
        titleEl.classList.add('source-codecollective-luma-title');
      }
      titleEl.innerHTML = `${eventTime} ${info.event.title}`;
      applyTagClasses(titleEl, info.event.extendedProps?.tags);
      eventEl.appendChild(titleEl);

      return { domNodes: [eventEl] };
    },
    eventDidMount: function (info) {
      if (isFeaturedSource(info.event.extendedProps?.source)) {
        const dayCell = info.el.closest('.fc-daygrid-day');
        if (dayCell) {
          dayCell.classList.add('source-codecollective-luma-day');
        }
      }
      if (!isMobile) {
        info.el.addEventListener('mouseenter', (event) => {
          showCalendarEventHover(info.event, event.clientX, event.clientY);
        });
        info.el.addEventListener('mousemove', (event) => {
          showCalendarEventHover(info.event, event.clientX, event.clientY);
        });
        info.el.addEventListener('mouseleave', hideHoverCard);
      }
    },
    // Add this: Callback for when view is rendered
    viewDidMount: function () {
      // Apply today highlighting after view changes
      highlightToday();
    }
  });
  calendar.render();
}

// Set up view selector buttons
function setupViewSelectors() {
  document.querySelectorAll('.view-selector').forEach(button => {
    button.addEventListener('click', function () {
      // Remove active class from all buttons
      document.querySelectorAll('.view-selector').forEach(btn => {
        btn.classList.remove('active');
      });

      // Add active class to clicked button
      this.classList.add('active');

      // Change calendar view
      const view = this.dataset.view;
      currentView = view;

      if (isMobile) {
        // Mobile: Always show cards, but filter/sort differently based on view
        handleMobileViewChange(view);
      } else {
        // Desktop: Use FullCalendar
        const effectiveView = (view === 'listAll') ? 'dayGridMonth' : view;
        calendar.changeView(effectiveView);

        // Reapply today highlighting after view change
        setTimeout(highlightToday, 100);
      }
    });
  });
}

// Handle view changes in mobile mode
function handleMobileViewChange(view) {
  const todayStart = getTodayStart();
  const eventsToShow = filterEventsBySelections(allEvents).filter(event =>
    isEventOnOrAfterToday(event.start, todayStart)
  );

  // Re-render mobile cards with filtered events
  initializeMobileCards(eventsToShow);
}

// Format event date for display
function formatEventDate(start, end) {
  if (!start) return '';

  const startDate = new Date(start);
  const options = {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit'
  };

  return startDate.toLocaleDateString('en-US', options);
}

// Close popup when clicking outside the content
window.onclick = function (event) {
  const popup = document.getElementById('event-popup');
  if (event.target === popup) {
    closeEventPopup();
  }
};
function populateCodeCollectiveEvents(events) {
  const container = document.getElementById('code-collective-events-container');
  if (!container) return;

  const codeCollectiveEvents = events.filter(event =>
    event.url && event.url.includes('code-collective')
  );

  if (codeCollectiveEvents.length === 0) {
    container.innerHTML = '<p style="text-align: center; color: #999; padding: 20px;">No upcoming Code Collective events at this time.</p>';
    return;
  }

  codeCollectiveEvents.sort((a, b) => new Date(a.startDate) - new Date(b.startDate));

  // Clear container and build with DOM methods
  container.innerHTML = '';

  codeCollectiveEvents.forEach((event, index) => {
    const startDate = new Date(event.startDate);
    const formattedDate = startDate.toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
    const formattedTime = startDate.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });

    // Create elements with DOM methods (prevents formatting issues)
    const eventCard = document.createElement('div');
    eventCard.className = 'cc-event-card';

    const eventLink = document.createElement('a');
    eventLink.href = event.url;
    eventLink.className = 'cc-event-card-link';
    eventLink.target = '_blank';
    eventLink.rel = 'noopener noreferrer';

    // Add image if available
    if (event.imageUrl) {
      const img = document.createElement('img');
      img.src = event.imageUrl;
      img.alt = event.name;
      img.className = 'event-card-image';
      img.loading = 'lazy';
      eventLink.appendChild(img);
    }

    const contentDiv = document.createElement('div');
    contentDiv.className = 'cc-event-card-content';

    const title = document.createElement('h3');
    title.className = 'cc-event-card-title';
    title.textContent = event.name; // Safe from HTML injection

    const dateDiv = document.createElement('div');
    dateDiv.className = 'cc-event-card-date';
    dateDiv.textContent = `${formattedDate} at ${formattedTime}`;

    const locationDiv = document.createElement('div');
    locationDiv.className = 'cc-event-card-location';
    locationDiv.textContent = event.location?.name || 'Location TBD';

    const descriptionDiv = document.createElement('div');
    descriptionDiv.className = 'cc-event-card-description';

    // Handle description safely
    let description = event.description || '';
    
    // Strip all HTML/markdown and just use plain text
    description = description
      .replace(/<[^>]*>/g, '') // Remove all HTML tags
      .replace(/\*\*(.*?)\*\*/g, '$1') // Remove markdown bold
      .replace(/\*(.*?)\*/g, '$1') // Remove markdown italic
      .replace(/\n+/g, ' ') // Replace newlines with spaces
      .trim();

    const truncatedDescription = description.length > 200 
      ? description.substring(0, 200) + '...' 
      : description;
    
    const needsTruncation = description.length > 200;
    const eventId = `event-${index}`;

    const shortDesc = document.createElement('div');
    shortDesc.id = `${eventId}-short`;
    shortDesc.textContent = truncatedDescription; // Safe from HTML injection
    if (!needsTruncation) shortDesc.style.display = 'block';

    descriptionDiv.appendChild(shortDesc);

    if (needsTruncation) {
      const fullDesc = document.createElement('div');
      fullDesc.id = `${eventId}-full`;
      fullDesc.style.display = 'none';
      fullDesc.textContent = description; // Safe from HTML injection

      const showMoreBtn = document.createElement('button');
      showMoreBtn.type = 'button';
      showMoreBtn.className = 'cc-show-more-btn';
      showMoreBtn.id = `${eventId}-btn`;
      showMoreBtn.textContent = 'Show more';
      showMoreBtn.onclick = () => toggleCcDescription(eventId);

      descriptionDiv.appendChild(fullDesc);
      descriptionDiv.appendChild(showMoreBtn);
    }

    // Assemble the card
    contentDiv.appendChild(title);
    contentDiv.appendChild(dateDiv);
    contentDiv.appendChild(locationDiv);
    contentDiv.appendChild(descriptionDiv);
    eventLink.appendChild(contentDiv);
    eventCard.appendChild(eventLink);
    container.appendChild(eventCard);
  });
}

// Toggle function for show more/less
function toggleCcDescription(eventId) {
  const shortDiv = document.getElementById(`${eventId}-short`);
  const fullDiv = document.getElementById(`${eventId}-full`);
  const btn = document.getElementById(`${eventId}-btn`);

  if (fullDiv.style.display === 'none') {
    shortDiv.style.display = 'none';
    fullDiv.style.display = 'block';
    btn.textContent = 'Show less';
  } else {
    shortDiv.style.display = 'block';
    fullDiv.style.display = 'none';
    btn.textContent = 'Show more';
  }
}
