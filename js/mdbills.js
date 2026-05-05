  const DATA_URL = 'https://mgaleg.maryland.gov/2026rs/misc/billsmasterlist/legislation.json';
  const LOCAL_DATA_URL = '/data/maryland_bills_2026.json';
  const HEARINGS_DATA_URL = '/data/maryland_bill_hearings_2026.json';
  const SPONSOR_DIRECTORY_URL = '/data/mga_sponsors_2026.json';
  const MGA_SESSION_SLUG = '2026RS';
  const FILTERS_STORAGE_KEY = 'mdbillsFiltersV1';
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

  const billsTableBody = document.getElementById('bills-table-body');
  const billFilterInput = document.getElementById('bill-filter');
  const sponsorFilterInput = document.getElementById('sponsor-filter');
  const categoryFilterInput = document.getElementById('category-filter');
  const upcomingOnlyToggle = document.getElementById('upcoming-only-toggle');
  const houseOnlyToggle = document.getElementById('house-only-toggle');
  const senateOnlyToggle = document.getElementById('senate-only-toggle');
  const passedOnlyToggle = document.getElementById('passed-only-toggle');
  const notPassedOnlyToggle = document.getElementById('not-passed-only-toggle');
  const searchClearButtons = [...document.querySelectorAll('.search-clear')];
  const sponsorTableBody = document.getElementById('sponsor-table-body');
  const categoryTableBody = document.getElementById('category-table-body');
  const billCount = document.getElementById('bill-count');
  const billUpdated = document.getElementById('bill-updated');
  const statusMessage = document.getElementById('status-message');
  const resetFiltersButton = document.getElementById('reset-filters');

  const billModal = document.getElementById('bill-modal');
  const billModalTitle = document.getElementById('bill-modal-title');
  const billModalContent = document.getElementById('bill-modal-content');
  const billModalClose = document.getElementById('bill-modal-close');
  const hoverCard = document.getElementById('hover-card');

  let allBills = [];
  let preparedBills = [];
  let activeSponsor = '';
  let activeCategories = [];
  let activeBill = null;
  let sponsorDirectory = [];
  let sponsorStats = new Map();
  let billHearingsByNumber = new Map();
  let hoverState = null;
  let hoverSwapTimer = null;
  let sortColumn = '';
  let sortDirection = ''; // 'asc', 'desc', or ''
  let showUpcomingOnly = false;
  let showHouseBills = true;
  let showSenateBills = true;
  let showPassedBills = true;
  let showNotPassedBills = true;

  const COLUMN_FONT_SIZE_CONFIG = {
    sponsor: { min: 10, max: 20, step: 1, default: 14, storageKey: 'mdbillsFontSizeSponsor' },
    category: { min: 10, max: 20, step: 1, default: 14, storageKey: 'mdbillsFontSizeCategory' },
    bills: { min: 10, max: 20, step: 1, default: 14, storageKey: 'mdbillsFontSizeBills' }
  };

  const columnFontSizes = {
    sponsor: COLUMN_FONT_SIZE_CONFIG.sponsor.default,
    category: COLUMN_FONT_SIZE_CONFIG.category.default,
    bills: COLUMN_FONT_SIZE_CONFIG.bills.default
  };

  function syncBillsDisplayFontSize() {
    document.documentElement.style.setProperty('--bills-font-size', `${columnFontSizes.bills}px`);
  }

  function loadColumnFontSizes() {
    for (const [column, config] of Object.entries(COLUMN_FONT_SIZE_CONFIG)) {
      try {
        const saved = localStorage.getItem(config.storageKey);
        if (saved) {
          const parsed = parseInt(saved, 10);
          if (!Number.isNaN(parsed) && parsed >= config.min && parsed <= config.max) {
            columnFontSizes[column] = parsed;
          }
        }
      } catch {
        // Ignore storage errors
      }
    }
    applyColumnFontSizes();
  }

  function applyColumnFontSizes() {
    for (const [column, size] of Object.entries(columnFontSizes)) {
      const element = document.getElementById(`${column}-column`);
      if (element) {
        element.style.setProperty('--column-font-size', `${size}px`);
      }
    }
    syncBillsDisplayFontSize();
  }

  function applyColumnFontSize(column) {
    const element = document.getElementById(`${column}-column`);
    if (element) {
      element.style.setProperty('--column-font-size', `${columnFontSizes[column]}px`);
    }
    if (column === 'bills') {
      syncBillsDisplayFontSize();
    }
  }

  function persistColumnFontSize(column) {
    try {
      const config = COLUMN_FONT_SIZE_CONFIG[column];
      if (config) {
        localStorage.setItem(config.storageKey, String(columnFontSizes[column]));
      }
    } catch {
      // Ignore storage errors
    }
  }

  function increaseColumnFontSize(column) {
    const config = COLUMN_FONT_SIZE_CONFIG[column];
    if (config && columnFontSizes[column] < config.max) {
      columnFontSizes[column] = Math.min(config.max, columnFontSizes[column] + config.step);
      applyColumnFontSize(column);
      persistColumnFontSize(column);
    }
  }

  function decreaseColumnFontSize(column) {
    const config = COLUMN_FONT_SIZE_CONFIG[column];
    if (config && columnFontSizes[column] > config.min) {
      columnFontSizes[column] = Math.max(config.min, columnFontSizes[column] - config.step);
      applyColumnFontSize(column);
      persistColumnFontSize(column);
    }
  }

  function loadPersistedFilters() {
    try {
      const raw = localStorage.getItem(FILTERS_STORAGE_KEY);
      if (!raw) {
        return {
          billQuery: '',
          sponsorQuery: '',
          categoryQuery: '',
          sponsor: '',
          categories: [],
          upcomingOnly: false,
          showHouseBills: true,
          showSenateBills: true,
          showPassedBills: true,
          showNotPassedBills: true
        };
      }
      const parsed = JSON.parse(raw);
      const parsedCategories = Array.isArray(parsed.categories)
        ? parsed.categories.map((value) => String(value || '')).filter(Boolean)
        : (parsed.category ? [String(parsed.category)] : []);
      return {
        billQuery: String(parsed.billQuery || ''),
        sponsorQuery: String(parsed.sponsorQuery || ''),
        categoryQuery: String(parsed.categoryQuery || ''),
        sponsor: String(parsed.sponsor || ''),
        categories: [...new Set(parsedCategories)],
        upcomingOnly: parsed.upcomingOnly === true || parsed.upcomingOnly === 'true',
        showHouseBills: parsed.showHouseBills !== false,
        showSenateBills: parsed.showSenateBills !== false,
        showPassedBills: parsed.showPassedBills !== false,
        showNotPassedBills: parsed.showNotPassedBills !== false
      };
    } catch {
      return {
        billQuery: '',
        sponsorQuery: '',
        categoryQuery: '',
        sponsor: '',
        categories: [],
        upcomingOnly: false,
        showHouseBills: true,
        showSenateBills: true,
        showPassedBills: true,
        showNotPassedBills: true
      };
    }
  }

  function persistFilters() {
    localStorage.setItem(FILTERS_STORAGE_KEY, JSON.stringify({
      billQuery: billFilterInput.value || '',
      sponsorQuery: sponsorFilterInput.value || '',
      categoryQuery: categoryFilterInput.value || '',
      sponsor: activeSponsor,
      categories: activeCategories,
      upcomingOnly: showUpcomingOnly,
      showHouseBills,
      showSenateBills,
      showPassedBills,
      showNotPassedBills
    }));
  }

  function clearPersistedFilters() {
    localStorage.removeItem(FILTERS_STORAGE_KEY);
  }

  function formatDate(value) {
    if (!value) {
      return '';
    }

    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
      return value;
    }

    return parsed.toLocaleString(undefined, {
      dateStyle: 'medium',
      timeStyle: value.includes('T') ? 'short' : undefined
    });
  }

  function summarizeSubjects(subjects) {
    return (subjects || []).map((subject) => subject.Name).filter(Boolean);
  }

  function escapeHtml(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  function getEarliestHearingDate(bill) {
    const hearingFields = [
      bill.HearingDateTimePrimaryHouseOfOrigin,
      bill.HearingDateTimeSecondaryHouseOfOrigin,
      bill.HearingDateTimePrimaryOppositeHouse,
      bill.HearingDateTimeSecondaryOppositeHouse
    ];

    const dates = hearingFields
      .filter(Boolean)
      .map((value) => new Date(value))
      .filter((date) => !Number.isNaN(date.getTime()))
      .sort((a, b) => a - b);

    return dates[0] || null;
  }

  function toDateOnlyTimestamp(date) {
    return new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
  }

  function isUpcomingBill(bill) {
    const hearingDate = getEarliestHearingDate(bill);
    if (!hearingDate) {
      return false;
    }

    const today = new Date();
    const todayTs = toDateOnlyTimestamp(today);
    return toDateOnlyTimestamp(hearingDate) >= todayTs;
  }

  function formatHearingDate(bill) {
    const hearingDate = getEarliestHearingDate(bill);
    return hearingDate ? hearingDate.toLocaleDateString(undefined, { dateStyle: 'medium' }) : '';
  }

  function searchableText(bill) {
    return [
      bill.BillNumber,
      bill.CrossfileBillNumber,
      bill.Title,
      bill.Status,
      bill.SponsorPrimary,
      bill.Synopsis,
      bill.CommitteePrimaryOrigin,
      bill.CommitteePrimaryOpposite,
      bill.BillType,
      bill.BillVersion,
      formatHearingDate(bill),
      ...summarizeSubjects(bill.BroadSubjects),
      ...summarizeSubjects(bill.NarrowSubjects),
      ...(bill.Sponsors || []).map((sponsor) => sponsor.Name)
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase();
  }

  function extractCategories(bill) {
    const names = [
      ...summarizeSubjects(bill.BroadSubjects),
      ...summarizeSubjects(bill.NarrowSubjects)
    ];
    return [...new Set(names.map((name) => String(name || '').trim()).filter(Boolean))];
  }

  function buildPreparedBills(bills) {
    return bills.map((bill, index) => ({
      index,
      bill,
      searchText: searchableText(bill),
      sponsor: String(bill.SponsorPrimary || '').trim(),
      categories: extractCategories(bill)
    }));
  }

  function updateSearchClearButtons() {
    for (const button of searchClearButtons) {
      const targetId = button.dataset.clearTarget;
      const target = targetId ? document.getElementById(targetId) : null;
      const hasValue = Boolean(target && target.value.trim());
      button.classList.toggle('visible', hasValue);
    }
  }

  function renderActiveFilterRowMarkup(kind, value) {
    if (!value) {
      return '';
    }
    const label = kind === 'sponsor' ? 'Selected sponsor' : 'Selected category';
    return `
      <div class="list-row list-row-active-filter">
        <div class="active-filter-summary">
          <span class="active-filter-label">${escapeHtml(label)}</span>
          <span class="active-filter-value">${escapeHtml(value)}</span>
        </div>
        <button type="button" class="active-filter-clear" data-clear-filter="${escapeHtml(kind)}" aria-label="Remove selected ${escapeHtml(kind)}">
          Remove
        </button>
      </div>
    `;
  }

  function renderActiveCategoryRowsMarkup(values) {
    if (!values.length) {
      return '';
    }
    return values.map((value) => `
      <div class="list-row list-row-active-filter">
        <div class="active-filter-summary">
          <span class="active-filter-label">Selected category</span>
          <span class="active-filter-value">${escapeHtml(value)}</span>
        </div>
        <button type="button" class="active-filter-clear" data-clear-filter="category" data-category-value="${escapeHtml(value)}" aria-label="Remove selected category ${escapeHtml(value)}">
          Remove
        </button>
      </div>
    `).join('');
  }

  function renderSponsorTable() {
    hideHoverCard();
    const sponsorQuery = sponsorFilterInput.value.trim().toLowerCase();
    const sponsorCounts = new Map();
    for (const bill of allBills) {
      const sponsor = String(bill.SponsorPrimary || 'Unknown sponsor').trim() || 'Unknown sponsor';
      sponsorCounts.set(sponsor, (sponsorCounts.get(sponsor) || 0) + 1);
    }

    const rows = [...sponsorCounts.entries()]
      .filter(([sponsor]) => !sponsorQuery || sponsor.toLowerCase().includes(sponsorQuery))
      .sort((a, b) => (b[1] - a[1]) || a[0].localeCompare(b[0]))
      .map(([sponsor, count]) => `
        <div class="list-row" data-sponsor="${escapeHtml(sponsor)}" tabindex="0">
          <button type="button" class="sponsor-button${sponsor === activeSponsor ? ' active' : ''}" data-sponsor="${escapeHtml(sponsor)}">
            ${escapeHtml(sponsor)}
          </button>
          <span class="list-count">${count.toLocaleString()}</span>
        </div>
      `)
      .join('');

    sponsorTableBody.innerHTML = `${renderActiveFilterRowMarkup('sponsor', activeSponsor)}${rows || '<div class="list-row"><span>No sponsor data available.</span><span class="list-count">0</span></div>'}`;
  }

  function renderCategoryTable() {
    hideHoverCard();
    const categoryQuery = categoryFilterInput.value.trim().toLowerCase();
    const relevantBills = preparedBills.filter((entry) => !activeSponsor || entry.sponsor === activeSponsor);
    const categoryCounts = new Map();

    for (const entry of relevantBills) {
      const categories = entry.categories.length ? entry.categories : ['Uncategorized'];
      for (const category of categories) {
        categoryCounts.set(category, (categoryCounts.get(category) || 0) + 1);
      }
    }

    activeCategories = activeCategories.filter((category) => categoryCounts.has(category));

    const rows = [...categoryCounts.entries()]
      .filter(([category]) => !categoryQuery || category.toLowerCase().includes(categoryQuery))
      .sort((a, b) => (b[1] - a[1]) || a[0].localeCompare(b[0]))
      .map(([category, count]) => `
        <div class="list-row" data-category="${escapeHtml(category)}" tabindex="0">
          <button type="button" class="sponsor-button${activeCategories.includes(category) ? ' active' : ''}" data-category="${escapeHtml(category)}">
            ${escapeHtml(category)}
          </button>
          <span class="list-count">${count.toLocaleString()}</span>
        </div>
      `)
      .join('');

    categoryTableBody.innerHTML = `${renderActiveCategoryRowsMarkup(activeCategories)}${rows || '<div class="list-row"><span>No category data available.</span><span class="list-count">0</span></div>'}`;
  }

  function updateActiveSponsor(nextSponsor) {
    activeSponsor = activeSponsor === nextSponsor ? '' : nextSponsor;
    renderSponsorTable();
    renderCategoryTable();
    persistFilters();
    renderBills();
  }

  function updateActiveCategory(nextCategory) {
    const category = String(nextCategory || '').trim();
    if (!category) {
      activeCategories = [];
    } else if (activeCategories.includes(category)) {
      activeCategories = activeCategories.filter((value) => value !== category);
    } else {
      activeCategories = [...activeCategories, category];
    }
    renderCategoryTable();
    persistFilters();
    renderBills();
  }

  function getBillChamber(bill) {
    const billNumber = String(bill?.BillNumber || '').trim().toUpperCase();
    if (billNumber.startsWith('HB') || billNumber.startsWith('HJ')) {
      return 'house';
    }
    if (billNumber.startsWith('SB') || billNumber.startsWith('SJ')) {
      return 'senate';
    }
    return '';
  }

  function didBillPass(bill) {
    const status = String(bill?.Status || '').toLowerCase();
    if (!status) {
      return false;
    }
    if (/\b(not passed|failed|withdrawn|vetoed)\b/.test(status)) {
      return false;
    }
    return /\b(approved by the governor|enacted|returned passed|passed)\b/.test(status);
  }

  function createBillRowMarkup(entry) {
    const { bill, index } = entry;
    const passed = didBillPass(bill);
    return `
      <tr>
        <td class="bill-number-cell" data-bill-index="${index}">${escapeHtml(bill.BillNumber || 'N/A')}</td>
        <td data-bill-index="${index}" tabindex="0">
          <p class="bill-title">
            <button
              type="button"
              class="bill-title-button"
              data-bill-index="${index}"
            >
              ${escapeHtml(bill.Title || 'Untitled Bill')}
            </button>
          </p>
        </td>
        <td data-sponsor-name="${escapeHtml(String(bill.SponsorPrimary || 'Unknown sponsor').trim() || 'Unknown sponsor')}">
          <button type="button" class="bill-sponsor-button" data-sponsor-name="${escapeHtml(String(bill.SponsorPrimary || 'Unknown sponsor').trim() || 'Unknown sponsor')}">
            ${escapeHtml(bill.SponsorPrimary || 'Unknown sponsor')}
          </button>
        </td>
        <td>${escapeHtml(bill.Status || 'Status unavailable')}</td>
        <td><span class="bill-status-cell ${passed ? 'bill-status-passed' : 'bill-status-not-passed'}">${passed ? 'Yes' : 'No'}</span></td>
        <td>${escapeHtml(formatHearingDate(bill) || 'N/A')}</td>
      </tr>
    `;
  }

  function stringifyValue(value) {
    if (value === null || value === undefined || value === '') {
      return 'N/A';
    }
    if (Array.isArray(value)) {
      return value.length ? value.join(', ') : 'N/A';
    }
    if (typeof value === 'object') {
      return JSON.stringify(value);
    }
    return String(value);
  }

  function getBillDetailsUrl(bill) {
    const billNumber = String(bill?.BillNumber || '').trim().toUpperCase();
    if (!billNumber) {
      return `https://mgaleg.maryland.gov/mgawebsite/Legislation/Search?ys=${encodeURIComponent(MGA_SESSION_SLUG)}`;
    }
    return `https://mgaleg.maryland.gov/mgawebsite/Legislation/Details/${encodeURIComponent(billNumber)}?ys=${encodeURIComponent(MGA_SESSION_SLUG)}`;
  }

  function getBillHearingDayUrl(bill) {
    const billNumber = String(bill?.BillNumber || '').trim().toUpperCase();
    if (!billNumber) {
      return 'https://mgaleg.maryland.gov/mgawebsite/Meetings';
    }
    return `https://mgaleg.maryland.gov/mgawebsite/Meetings/Day/${encodeURIComponent(billNumber)}`;
  }

  function getWitnessSignupUrl() {
    return 'https://mgaleg.maryland.gov/mgawebsite/MyMGATracking/WitnessSignup';
  }

  function getBillHearingRecord(bill) {
    const billNumber = String(bill?.BillNumber || '').trim().toUpperCase();
    return billNumber ? (billHearingsByNumber.get(billNumber) || null) : null;
  }

  function renderBillActionLinks(bill) {
    const hearingRecord = getBillHearingRecord(bill);
    const detailsUrl = getBillDetailsUrl(bill);
    const hearingDayUrl = hearingRecord?.hearing_day_url || getBillHearingDayUrl(bill);
    const testifyUrl = hearingRecord?.testify_url || hearingDayUrl;
    const directSignup = Boolean(hearingRecord?.has_testify_signup);
    const ctaHint = directSignup
      ? 'Direct witness signup from scraped MGA hearing schedule'
      : 'Opens the hearing day page to check testimony availability';
    return `
      <section class="bill-modal-links" aria-label="Maryland General Assembly bill links">
        <a class="bill-modal-link bill-modal-link-primary" href="${escapeHtml(testifyUrl)}" target="_blank" rel="noopener noreferrer">
          <span class="bill-modal-link-label">Testify on this bill</span>
          <span class="bill-modal-link-url">${escapeHtml(ctaHint)}</span>
        </a>
        <a class="bill-modal-link" href="${escapeHtml(detailsUrl)}" target="_blank" rel="noopener noreferrer">
          <span class="bill-modal-link-label">Bill details</span>
          <span class="bill-modal-link-url">${escapeHtml(detailsUrl)}</span>
        </a>
        <a class="bill-modal-link" href="${escapeHtml(hearingDayUrl)}" target="_blank" rel="noopener noreferrer">
          <span class="bill-modal-link-label">Hearing day</span>
          <span class="bill-modal-link-url">${escapeHtml(hearingDayUrl)}</span>
        </a>
        <a class="bill-modal-link" href="${escapeHtml(getWitnessSignupUrl())}" target="_blank" rel="noopener noreferrer">
          <span class="bill-modal-link-label">Witness signup</span>
          <span class="bill-modal-link-url">${escapeHtml(getWitnessSignupUrl())}</span>
        </a>
      </section>
    `;
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
      const [last, first] = clean.split(',').map((part) => part.trim()).filter(Boolean);
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

    // First pass: exact normalized matches against heading and slug.
    for (const rec of sponsorDirectory) {
      const heading = normalizePersonName(rec.name_heading || '');
      const slug = normalizePersonName(String(rec.slug || '').replace(/[0-9]+$/g, ''));
      if (targets.includes(heading) || targets.includes(slug)) {
        return rec;
      }
    }

    // Second pass: last-name fallback if unique.
    const targetLast = targets[0].split(' ').filter(Boolean).at(-1);
    if (!targetLast) {
      return null;
    }
    const matches = sponsorDirectory.filter((rec) => {
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

  function truncateText(text, maxLength) {
    const normalized = String(text || '').replace(/\s+/g, ' ').trim();
    if (!normalized) {
      return '';
    }
    if (normalized.length <= maxLength) {
      return normalized;
    }
    return `${normalized.slice(0, Math.max(0, maxLength - 1)).trimEnd()}…`;
  }

  function rebuildSponsorStats() {
    const nextStats = new Map();
    for (const bill of allBills) {
      const primary = String(bill.SponsorPrimary || 'Unknown sponsor').trim() || 'Unknown sponsor';
      if (!nextStats.has(primary)) {
        nextStats.set(primary, { primaryCount: 0, involvedCount: 0 });
      }
      nextStats.get(primary).primaryCount += 1;

      const participants = new Set([primary]);
      for (const sponsor of (bill.Sponsors || [])) {
        const name = String(sponsor.Name || '').trim();
        if (name) {
          participants.add(name);
        }
      }
      for (const name of participants) {
        if (!nextStats.has(name)) {
          nextStats.set(name, { primaryCount: 0, involvedCount: 0 });
        }
        nextStats.get(name).involvedCount += 1;
      }
    }
    sponsorStats = nextStats;
  }

  function inferMarylandRegionFromCounty(countyValue) {
    const value = String(countyValue || '').toLowerCase();
    if (!value) {
      return '';
    }
    if (value.includes('allegany') || value.includes('garrett') || value.includes('washington')) {
      return 'Western Maryland';
    }
    if (value.includes('cecil') || value.includes('kent') || value.includes('queen anne')
      || value.includes('caroline') || value.includes('talbot') || value.includes('dorchester')
      || value.includes('wicomico') || value.includes('somerset') || value.includes('worcester')) {
      return 'Eastern Shore';
    }
    if (value.includes('calvert') || value.includes('charles') || value.includes('st. mary')
      || value.includes('st mary')) {
      return 'Southern Maryland';
    }
    if (value.includes('anne arundel') || value.includes('baltimore') || value.includes('howard')
      || value.includes('harford') || value.includes('carroll') || value.includes('frederick')
      || value.includes('montgomery') || value.includes('prince george')) {
      return 'Central Maryland';
    }
    return 'Maryland';
  }

  function buildSponsorHoverMarkup(sponsorName) {
    const directoryRecord = findDirectoryRecordBySponsorName(sponsorName);
    const stats = sponsorStats.get(sponsorName) || { primaryCount: 0, involvedCount: 0 };
    const imageMarkup = buildSponsorImageMarkup(sponsorName, directoryRecord);
    const metaParts = [];
    if (directoryRecord?.party) {
      metaParts.push(String(directoryRecord.party));
    }
    if (directoryRecord?.chamber) {
      metaParts.push(String(directoryRecord.chamber));
    }
    if (directoryRecord?.district) {
      metaParts.push(`District ${directoryRecord.district}`);
    }
    if (directoryRecord?.county) {
      metaParts.push(String(directoryRecord.county));
    }
    const region = inferMarylandRegionFromCounty(directoryRecord?.county || '');
    if (region) {
      metaParts.push(region);
    }
    return `
      <p class="hover-card-kicker">Sponsor</p>
      <h3>${escapeHtml(sponsorName)}</h3>
      <p class="hover-card-meta">Primary bills: ${stats.primaryCount.toLocaleString()} | Bills involved: ${stats.involvedCount.toLocaleString()}</p>
      ${metaParts.length ? `<p class="hover-card-meta">${escapeHtml(metaParts.join(' | '))}</p>` : ''}
      ${imageMarkup}
    `;
  }

  function buildBillHoverMarkup(bill) {
    const sponsorName = String(bill.SponsorPrimary || 'Unknown sponsor').trim() || 'Unknown sponsor';
    const synopsis = String(bill.Synopsis || '').trim();
    const categories = extractCategories(bill).slice(0, 3);
    const directoryRecord = findDirectoryRecordBySponsorName(sponsorName);
    const imageMarkup = buildSponsorImageMarkup(sponsorName, directoryRecord);
    return `
      <p class="hover-card-kicker">Bill</p>
      <h3>${escapeHtml(bill.BillNumber || 'N/A')} ${escapeHtml(bill.Title || '')}</h3>
      <p class="hover-card-meta">Sponsor: ${escapeHtml(sponsorName)}</p>
      <p class="hover-card-meta">Status: ${escapeHtml(bill.Status || 'Status unavailable')}</p>
      <p class="hover-card-meta">Hearing: ${escapeHtml(formatHearingDate(bill) || 'N/A')}</p>
      ${categories.length ? `<p class="hover-card-meta hover-card-meta-accent">Subjects: ${escapeHtml(categories.join(' | '))}</p>` : ''}
      ${synopsis ? `<p>${escapeHtml(synopsis)}</p>` : ''}
      ${imageMarkup}
    `;
  }

  function buildCategoryHoverMarkup(categoryName) {
    const relevantEntries = preparedBills
      .filter((entry) => !activeSponsor || entry.sponsor === activeSponsor)
      .filter((entry) => categoryName === 'Uncategorized'
        ? entry.categories.length === 0
        : entry.categories.includes(categoryName));

    const statuses = new Map();
    const sponsors = new Map();
    for (const entry of relevantEntries) {
      const bill = entry.bill;
      const status = String(bill.Status || 'Unknown').trim() || 'Unknown';
      statuses.set(status, (statuses.get(status) || 0) + 1);
      const sponsor = String(bill.SponsorPrimary || 'Unknown sponsor').trim() || 'Unknown sponsor';
      sponsors.set(sponsor, (sponsors.get(sponsor) || 0) + 1);
    }

    const topStatuses = [...statuses.entries()]
      .sort((a, b) => (b[1] - a[1]) || a[0].localeCompare(b[0]))
      .slice(0, 5)
      .map(([name, count]) => `${name} (${count})`);
    const topSponsors = [...sponsors.entries()]
      .sort((a, b) => (b[1] - a[1]) || a[0].localeCompare(b[0]))
      .slice(0, 5)
      .map(([name, count]) => `${name} (${count})`);

    const billTitles = relevantEntries
      .slice(0, 5)
      .map((entry) => `${entry.bill.BillNumber || 'N/A'}: ${truncateText(entry.bill.Title, 60)}`);

    return `
      <p class="hover-card-kicker">Category</p>
      <h3>${escapeHtml(categoryName)}</h3>
      <p class="hover-card-meta">Bills in category: ${relevantEntries.length.toLocaleString()}</p>
      ${activeSponsor ? `<p class="hover-card-meta">Sponsor filter: ${escapeHtml(activeSponsor)}</p>` : ''}
      ${billTitles.length ? `<p class="hover-card-meta hover-card-meta-accent">Bill titles:</p><p class="hover-card-meta">${billTitles.map((t) => escapeHtml(t)).join('<br>')}</p>` : ''}
      ${topStatuses.length ? `<p class="hover-card-meta hover-card-meta-accent">Top statuses: ${escapeHtml(topStatuses.join(' | '))}</p>` : ''}
      ${topSponsors.length ? `<p class="hover-card-meta">Top sponsors: ${escapeHtml(topSponsors.join(' | '))}</p>` : ''}
    `;
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
    if (!hoverCard || billModal.classList.contains('open')) {
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

  function showSponsorHover(sponsorName, side = 'left') {
    hoverState = { type: 'sponsor', name: sponsorName };
    showHoverCard(buildSponsorHoverMarkup(sponsorName), 14, 120);
    if (side === 'right') {
      hoverCard.classList.add('right-overlay');
      positionRightOverlayCard();
    } else {
      hoverCard.classList.add('left-overlay');
      positionLeftOverlayCard();
    }
  }

  function showCategoryHover(categoryName) {
    hoverState = { type: 'category', name: categoryName };
    showHoverCard(buildCategoryHoverMarkup(categoryName), 14, 120);
    hoverCard.classList.add('right-overlay');
    positionRightOverlayCard();
  }

  function showBillHover(bill, positionSource) {
    hoverState = { type: 'bill', id: bill.BillID || bill.BillNumber || '' };
    showHoverCard(buildBillHoverMarkup(bill), 14, 120);
    hoverCard.classList.add('left-overlay');
    positionLeftOverlayCard();
  }

  function renderBillModal(bill) {
    const broad = summarizeSubjects(bill.BroadSubjects);
    const narrow = summarizeSubjects(bill.NarrowSubjects);
    const sponsors = (bill.Sponsors || []).map((s) => s.Name).filter(Boolean);
    const fields = [
      ['Bill Number', bill.BillNumber],
      ['Crossfile Bill Number', bill.CrossfileBillNumber],
      ['Title', bill.Title],
      ['Status', bill.Status],
      ['Primary Sponsor', bill.SponsorPrimary],
      ['Sponsors', sponsors],
      ['Synopsis', bill.Synopsis],
      ['Year/Session', bill.YearAndSession],
      ['Bill Type', bill.BillType],
      ['Bill Version', bill.BillVersion],
      ['Committee (Origin)', bill.CommitteePrimaryOrigin],
      ['Committee (Opposite)', bill.CommitteePrimaryOpposite],
      ['First Reading (House of Origin)', formatDate(bill.FirstReadingDateHouseOfOrigin)],
      ['Status Current As Of', formatDate(bill.StatusCurrentAsOf)],
      ['Broad Subjects', broad],
      ['Narrow Subjects', narrow]
    ];

    const knownKeys = new Set([
      'BillID',
      'BillNumber',
      'CrossfileBillNumber',
      'Title',
      'Status',
      'SponsorPrimary',
      'Sponsors',
      'Synopsis',
      'YearAndSession',
      'BillType',
      'BillVersion',
      'CommitteePrimaryOrigin',
      'CommitteePrimaryOpposite',
      'FirstReadingDateHouseOfOrigin',
      'StatusCurrentAsOf',
      'BroadSubjects',
      'NarrowSubjects'
    ]);

    for (const [key, value] of Object.entries(bill)) {
      if (!knownKeys.has(key)) {
        fields.push([key, value]);
      }
    }

    billModalTitle.textContent = bill.BillNumber
      ? `${bill.BillNumber} Details`
      : 'Bill Details';
    billModalContent.innerHTML = `
      ${renderBillActionLinks(bill)}
      <table class="bill-detail-table">
        <tbody>
          ${fields.map(([label, value]) => `
            <tr>
              <th>${escapeHtml(label)}</th>
              <td>${escapeHtml(stringifyValue(value))}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  }

  function openBillModal(bill) {
    activeBill = bill;
    renderBillModal(bill);
    billModal.classList.add('open');
    billModalClose.focus();
  }

  function billIncludesSponsor(bill, sponsorName) {
    if ((String(bill.SponsorPrimary || '').trim() || 'Unknown sponsor') === sponsorName) {
      return true;
    }
    const listedSponsors = (bill.Sponsors || []).map((s) => String(s.Name || '').trim());
    return listedSponsors.includes(sponsorName);
  }

  function renderSponsorModal(sponsorName) {
    const involvedBills = allBills.filter((bill) => billIncludesSponsor(bill, sponsorName));
    const primaryBills = allBills.filter((bill) => (String(bill.SponsorPrimary || '').trim() || 'Unknown sponsor') === sponsorName);
    const sponsorRecords = [];
    for (const bill of involvedBills) {
      for (const sponsor of (bill.Sponsors || [])) {
        if (String(sponsor.Name || '').trim() === sponsorName) {
          sponsorRecords.push(sponsor);
        }
      }
    }

    const statusCounts = new Map();
    const categoryCounts = new Map();
    for (const bill of involvedBills) {
      const status = String(bill.Status || 'Unknown').trim() || 'Unknown';
      statusCounts.set(status, (statusCounts.get(status) || 0) + 1);
      const categories = extractCategories(bill);
      const categoryList = categories.length ? categories : ['Uncategorized'];
      for (const category of categoryList) {
        categoryCounts.set(category, (categoryCounts.get(category) || 0) + 1);
      }
    }

    const extraRecordValues = new Map();
    for (const record of sponsorRecords) {
      for (const [key, value] of Object.entries(record)) {
        if (key === 'Name') {
          continue;
        }
        if (!extraRecordValues.has(key)) {
          extraRecordValues.set(key, new Set());
        }
        extraRecordValues.get(key).add(stringifyValue(value));
      }
    }

    const fields = [
      ['Sponsor Name', sponsorName],
      ['Primary Sponsored Bills', primaryBills.length.toLocaleString()],
      ['All Bills Involved', involvedBills.length.toLocaleString()],
      ['Primary Bill Numbers', primaryBills.map((bill) => bill.BillNumber).filter(Boolean)],
      ['All Bill Numbers', involvedBills.map((bill) => bill.BillNumber).filter(Boolean)],
      ['Status Breakdown', [...statusCounts.entries()].sort((a, b) => b[1] - a[1]).map(([k, v]) => `${k} (${v})`)],
      ['Category Breakdown', [...categoryCounts.entries()].sort((a, b) => b[1] - a[1]).map(([k, v]) => `${k} (${v})`)],
      ['Sponsor Record Count', sponsorRecords.length.toLocaleString()]
    ];

    for (const [key, values] of extraRecordValues.entries()) {
      fields.push([`Sponsor ${key}`, [...values]]);
    }

    const directoryRecord = findDirectoryRecordBySponsorName(sponsorName);
    let imageSection = '';
    if (directoryRecord) {
      fields.push(['Directory Name', directoryRecord.name_heading || 'N/A']);
      fields.push(['Chamber', directoryRecord.chamber || 'N/A']);
      fields.push(['District', directoryRecord.district || 'N/A']);
      fields.push(['County', directoryRecord.county || 'N/A']);
      fields.push(['Party', directoryRecord.party || 'N/A']);
      fields.push(['Committee Assignment(s)', directoryRecord.committee_assignments || []]);
      fields.push(['Contact Emails', directoryRecord.contact_emails || []]);
      fields.push(['Annapolis Info', directoryRecord.annapolis_info || []]);
      fields.push(['Interim Info', directoryRecord.interim_info || []]);
      fields.push(['MGA Detail URL', directoryRecord.detail_url || 'N/A']);

      const imageBlocks = [];
      const portraitSrc = getImageSource(directoryRecord.portrait_image);
      if (portraitSrc) {
        imageBlocks.push(`
          <figure>
            <img alt="Sponsor portrait for ${escapeHtml(sponsorName)}" src="${escapeHtml(portraitSrc)}">
            <figcaption>Portrait</figcaption>
          </figure>
        `);
      }
      const standardizedSrc = getImageSource(directoryRecord.standardized_district_map_image);
      if (standardizedSrc) {
        imageBlocks.push(`
          <figure>
            <img alt="Standardized Maryland district map for ${escapeHtml(sponsorName)}" src="${escapeHtml(standardizedSrc)}">
            <figcaption>Maryland District Context Map</figcaption>
          </figure>
        `);
      }

      if (imageBlocks.length) {
        imageSection = `<section class="sponsor-modal-images">${imageBlocks.join('')}</section>`;
      }
    }

    billModalTitle.textContent = `Sponsor: ${sponsorName}`;
    billModalContent.innerHTML = `
      ${imageSection}
      <table class="bill-detail-table">
        <tbody>
          ${fields.map(([label, value]) => `
            <tr>
              <th>${escapeHtml(label)}</th>
              <td>${escapeHtml(stringifyValue(value))}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  }

  function openSponsorModal(sponsorName) {
    hideHoverCard();
    activeBill = null;
    renderSponsorModal(sponsorName);
    billModal.classList.add('open');
    billModalClose.focus();
  }

  function closeBillModal() {
    activeBill = null;
    billModal.classList.remove('open');
  }

  function getSortValue(entry, column) {
    const { bill } = entry;
    switch (column) {
      case 'billNumber':
        return String(bill.BillNumber || '').toLowerCase();
      case 'title':
        return String(bill.Title || '').toLowerCase();
      case 'sponsor':
        return String(bill.SponsorPrimary || '').toLowerCase();
      case 'status':
        return String(bill.Status || '').toLowerCase();
      case 'passed':
        return didBillPass(bill) ? 1 : 0;
      case 'hearingDate': {
        const hearingDate = getEarliestHearingDate(bill);
        return hearingDate ? toDateOnlyTimestamp(hearingDate) : Number.POSITIVE_INFINITY;
      }
      default:
        return '';
    }
  }

  function sortEntries(entries, column, direction) {
    if (!column || !direction) {
      return entries;
    }
    const sorted = [...entries];
    sorted.sort((a, b) => {
      const aVal = getSortValue(a, column);
      const bVal = getSortValue(b, column);
      if (aVal < bVal) return direction === 'asc' ? -1 : 1;
      if (aVal > bVal) return direction === 'asc' ? 1 : -1;
      return 0;
    });
    return sorted;
  }

  function updateSortIndicators() {
    document.querySelectorAll('.bills-table th.sortable').forEach((th) => {
      th.classList.remove('sort-asc', 'sort-desc');
      if (th.dataset.sort === sortColumn) {
        if (sortDirection === 'asc') {
          th.classList.add('sort-asc');
        } else if (sortDirection === 'desc') {
          th.classList.add('sort-desc');
        }
      }
    });
  }

  function cycleSort(column) {
    if (sortColumn === column) {
      // Cycle: asc -> desc -> none
      if (sortDirection === 'asc') {
        sortDirection = 'desc';
      } else if (sortDirection === 'desc') {
        sortColumn = '';
        sortDirection = '';
      }
    } else {
      sortColumn = column;
      sortDirection = 'asc';
    }
    updateSortIndicators();
    renderBills();
  }

  function renderBills() {
    hideHoverCard();
    const query = billFilterInput.value.trim().toLowerCase();
    let filteredEntries = preparedBills
      .filter((entry) => !activeSponsor || entry.sponsor === activeSponsor)
      .filter((entry) => !activeCategories.length
        || activeCategories.some((category) => (
          (category === 'Uncategorized' && entry.categories.length === 0)
          || entry.categories.includes(category)
        )))
      .filter((entry) => !showUpcomingOnly || isUpcomingBill(entry.bill))
      .filter((entry) => {
        const chamber = getBillChamber(entry.bill);
        if (chamber === 'house') {
          return showHouseBills;
        }
        if (chamber === 'senate') {
          return showSenateBills;
        }
        return true;
      })
      .filter((entry) => {
        const passed = didBillPass(entry.bill);
        return (passed && showPassedBills) || (!passed && showNotPassedBills);
      })
      .filter((entry) => !query || entry.searchText.includes(query));

    filteredEntries = sortEntries(filteredEntries, sortColumn, sortDirection);

    billCount.textContent = `${filteredEntries.length.toLocaleString()} of ${allBills.length.toLocaleString()} bills shown`;
    statusMessage.textContent = filteredEntries.length
      ? ''
      : 'No bills matched that filter.';

    billsTableBody.innerHTML = filteredEntries.length
      ? filteredEntries.map(createBillRowMarkup).join('')
      : '<tr><td colspan="6">No bills matched that filter.</td></tr>';
  }

  function resetFilters() {
    activeSponsor = '';
    activeCategories = [];
    sortColumn = '';
    sortDirection = '';
    billFilterInput.value = '';
    sponsorFilterInput.value = '';
    categoryFilterInput.value = '';
    showUpcomingOnly = false;
    showHouseBills = true;
    showSenateBills = true;
    showPassedBills = true;
    showNotPassedBills = true;
    if (upcomingOnlyToggle) {
      upcomingOnlyToggle.checked = false;
    }
    if (houseOnlyToggle) {
      houseOnlyToggle.checked = true;
    }
    if (senateOnlyToggle) {
      senateOnlyToggle.checked = true;
    }
    if (passedOnlyToggle) {
      passedOnlyToggle.checked = true;
    }
    if (notPassedOnlyToggle) {
      notPassedOnlyToggle.checked = true;
    }
    clearPersistedFilters();
    updateSortIndicators();
    renderSponsorTable();
    renderCategoryTable();
    renderBills();
    updateSearchClearButtons();
  }

  async function fetchBillsData() {
    const errors = [];

    for (const source of DATA_SOURCES) {
      try {
        const response = await fetch(source.url, { cache: 'no-store' });
        if (!response.ok) {
          throw new Error(`status ${response.status}`);
        }

        // Some proxies return JSON as plain text, so parse defensively.
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

  async function loadBills() {
    try {
      try {
        const hearingsResp = await fetch(HEARINGS_DATA_URL, { cache: 'no-store' });
        if (hearingsResp.ok) {
          const hearingsPayload = await hearingsResp.json();
          const hearingRecords = hearingsPayload && typeof hearingsPayload === 'object' ? hearingsPayload.records : null;
          billHearingsByNumber = new Map(Object.entries(hearingRecords || {}));
        }
      } catch (hearingErr) {
        console.warn('Hearing testimony cache unavailable:', hearingErr);
      }

      // Load sponsor directory data for richer sponsor modal details.
      try {
        const sponsorResp = await fetch(SPONSOR_DIRECTORY_URL, { cache: 'no-store' });
        if (sponsorResp.ok) {
          const sponsorPayload = await sponsorResp.json();
          sponsorDirectory = Array.isArray(sponsorPayload.records) ? sponsorPayload.records : [];
        }
      } catch (sponsorErr) {
        console.warn('Sponsor directory unavailable:', sponsorErr);
      }

      const persisted = loadPersistedFilters();
      const { bills, source } = await fetchBillsData();
      allBills = bills;
      preparedBills = buildPreparedBills(allBills);
      rebuildSponsorStats();
      billFilterInput.value = persisted.billQuery;
      sponsorFilterInput.value = persisted.sponsorQuery;
      categoryFilterInput.value = persisted.categoryQuery;
      showUpcomingOnly = Boolean(persisted.upcomingOnly);
      if (upcomingOnlyToggle) {
        upcomingOnlyToggle.checked = showUpcomingOnly;
      }
      showHouseBills = persisted.showHouseBills !== false;
      showSenateBills = persisted.showSenateBills !== false;
      showPassedBills = persisted.showPassedBills !== false;
      showNotPassedBills = persisted.showNotPassedBills !== false;
      if (houseOnlyToggle) {
        houseOnlyToggle.checked = showHouseBills;
      }
      if (senateOnlyToggle) {
        senateOnlyToggle.checked = showSenateBills;
      }
      if (passedOnlyToggle) {
        passedOnlyToggle.checked = showPassedBills;
      }
      if (notPassedOnlyToggle) {
        notPassedOnlyToggle.checked = showNotPassedBills;
      }
      activeSponsor = persisted.sponsor;
      activeCategories = persisted.categories;
      const sponsorSet = new Set(allBills.map((bill) => String(bill.SponsorPrimary || '').trim() || 'Unknown sponsor'));
      if (activeSponsor && !sponsorSet.has(activeSponsor)) {
        activeSponsor = '';
      }
      renderSponsorTable();
      renderCategoryTable();
      persistFilters();
      updateSearchClearButtons();
      const latestTimestamp = allBills
        .map((bill) => bill.StatusCurrentAsOf)
        .filter(Boolean)
        .sort()
        .at(-1);

      billUpdated.textContent = latestTimestamp
        ? `Data current as of ${formatDate(latestTimestamp)}`
        : '';
      statusMessage.textContent = source === 'corsproxy'
        ? 'Loaded via fallback proxy because browser CORS blocks direct source on localhost.'
        : '';
      renderBills();
    } catch (error) {
      statusMessage.textContent = `Unable to load Maryland bill data: ${error.message}`;
      billCount.textContent = '0 bills shown';
      billUpdated.textContent = '';
    }
  }

  billFilterInput.addEventListener('input', renderBills);
  billFilterInput.addEventListener('input', persistFilters);
  billFilterInput.addEventListener('input', updateSearchClearButtons);
  sponsorFilterInput.addEventListener('input', renderSponsorTable);
  sponsorFilterInput.addEventListener('input', persistFilters);
  sponsorFilterInput.addEventListener('input', updateSearchClearButtons);
  categoryFilterInput.addEventListener('input', renderCategoryTable);
  categoryFilterInput.addEventListener('input', persistFilters);
  categoryFilterInput.addEventListener('input', updateSearchClearButtons);
  if (upcomingOnlyToggle) {
    upcomingOnlyToggle.addEventListener('change', () => {
      showUpcomingOnly = upcomingOnlyToggle.checked;
      persistFilters();
      renderBills();
    });
  }
  if (houseOnlyToggle) {
    houseOnlyToggle.addEventListener('change', () => {
      showHouseBills = houseOnlyToggle.checked;
      persistFilters();
      renderBills();
    });
  }
  if (senateOnlyToggle) {
    senateOnlyToggle.addEventListener('change', () => {
      showSenateBills = senateOnlyToggle.checked;
      persistFilters();
      renderBills();
    });
  }
  if (passedOnlyToggle) {
    passedOnlyToggle.addEventListener('change', () => {
      showPassedBills = passedOnlyToggle.checked;
      persistFilters();
      renderBills();
    });
  }
  if (notPassedOnlyToggle) {
    notPassedOnlyToggle.addEventListener('change', () => {
      showNotPassedBills = notPassedOnlyToggle.checked;
      persistFilters();
      renderBills();
    });
  }
  for (const button of searchClearButtons) {
    button.addEventListener('click', () => {
      const targetId = button.dataset.clearTarget;
      const target = targetId ? document.getElementById(targetId) : null;
      if (!target) {
        return;
      }
      target.value = '';
      target.focus();
      if (target === billFilterInput) {
        renderBills();
      } else if (target === sponsorFilterInput) {
        renderSponsorTable();
      } else if (target === categoryFilterInput) {
        renderCategoryTable();
      }
      persistFilters();
      updateSearchClearButtons();
    });
  }
  sponsorTableBody.addEventListener('click', (event) => {
    const clearButton = event.target.closest('.active-filter-clear');
    if (clearButton) {
      updateActiveSponsor('');
      return;
    }
    const button = event.target.closest('.sponsor-button');
    if (!button) {
      return;
    }
    updateActiveSponsor(button.dataset.sponsor || '');
  });
  categoryTableBody.addEventListener('click', (event) => {
    const clearButton = event.target.closest('.active-filter-clear');
    if (clearButton) {
      const categoryValue = clearButton.dataset.categoryValue || '';
      updateActiveCategory(categoryValue);
      return;
    }
    const button = event.target.closest('.sponsor-button');
    if (!button) {
      return;
    }
    updateActiveCategory(button.dataset.category || '');
  });
  billsTableBody.addEventListener('click', (event) => {
    const billButton = event.target.closest('.bill-title-button');
    if (billButton) {
      const index = Number(billButton.dataset.billIndex);
      const bill = Number.isInteger(index) ? allBills[index] : null;
      if (bill) {
        hideHoverCard();
        openBillModal(bill);
      }
      return;
    }
    const sponsorButton = event.target.closest('.bill-sponsor-button');
    if (sponsorButton) {
      updateActiveSponsor(sponsorButton.dataset.sponsorName || 'Unknown sponsor');
    }
  });
  sponsorTableBody.addEventListener('mouseover', (event) => {
    const row = event.target.closest('[data-sponsor]');
    if (!row) {
      return;
    }
    const sponsorName = String(row.dataset.sponsor || '').trim();
    if (!sponsorName) {
      return;
    }
    showSponsorHover(sponsorName, 'right');
  });
  sponsorTableBody.addEventListener('mousemove', (event) => {
    if (!hoverState || !hoverCard.classList.contains('open')
      || hoverCard.classList.contains('left-overlay')
      || hoverCard.classList.contains('right-overlay')) {
      return;
    }
    positionHoverCard(event.clientX, event.clientY);
  });
  sponsorTableBody.addEventListener('mouseleave', hideHoverCard);
  sponsorTableBody.addEventListener('focusin', (event) => {
    const row = event.target.closest('[data-sponsor]');
    if (!row) {
      return;
    }
    const sponsorName = String(row.dataset.sponsor || '').trim();
    if (sponsorName) {
      showSponsorHover(sponsorName, 'right');
    }
  });
  sponsorTableBody.addEventListener('focusout', hideHoverCard);
  categoryTableBody.addEventListener('mouseover', (event) => {
    const row = event.target.closest('[data-category]');
    if (!row) {
      return;
    }
    const categoryName = String(row.dataset.category || '').trim();
    if (!categoryName) {
      return;
    }
    showCategoryHover(categoryName);
  });
  categoryTableBody.addEventListener('mouseleave', hideHoverCard);
  categoryTableBody.addEventListener('focusin', (event) => {
    const row = event.target.closest('[data-category]');
    if (!row) {
      return;
    }
    const categoryName = String(row.dataset.category || '').trim();
    if (categoryName) {
      showCategoryHover(categoryName);
    }
  });
  categoryTableBody.addEventListener('focusout', hideHoverCard);
  billsTableBody.addEventListener('mouseover', (event) => {
    const sponsorTarget = event.target.closest('[data-sponsor-name]');
    if (sponsorTarget) {
      const sponsorName = String(sponsorTarget.dataset.sponsorName || '').trim();
      if (sponsorName) {
        showSponsorHover(sponsorName, 'left');
      }
      return;
    }
    const billTarget = event.target.closest('[data-bill-index]');
    if (!billTarget) {
      hideHoverCard();
      return;
    }
    const index = Number(billTarget.dataset.billIndex);
    const bill = Number.isInteger(index) ? allBills[index] : null;
    if (bill) {
      showBillHover(bill, billTarget);
    }
  });
  billsTableBody.addEventListener('mousemove', (event) => {
    if (!hoverState || !hoverCard.classList.contains('open')
      || hoverCard.classList.contains('left-overlay')
      || hoverCard.classList.contains('right-overlay')) {
      return;
    }
    positionHoverCard(event.clientX, event.clientY);
  });
  billsTableBody.addEventListener('mouseleave', hideHoverCard);
  billsTableBody.addEventListener('focusin', (event) => {
    const sponsorTarget = event.target.closest('[data-sponsor-name]');
    if (sponsorTarget) {
      const sponsorName = String(sponsorTarget.dataset.sponsorName || '').trim();
      if (sponsorName) {
        showSponsorHover(sponsorName, 'left');
      }
      return;
    }
    const billTarget = event.target.closest('[data-bill-index]');
    if (!billTarget) {
      return;
    }
    const index = Number(billTarget.dataset.billIndex);
    const bill = Number.isInteger(index) ? allBills[index] : null;
    if (bill) {
      showBillHover(bill, billTarget);
    }
  });
  billsTableBody.addEventListener('focusout', hideHoverCard);
  billModalClose.addEventListener('click', closeBillModal);
  billModal.addEventListener('click', (event) => {
    if (event.target === billModal) {
      closeBillModal();
    }
  });
  window.addEventListener('scroll', hideHoverCard, { passive: true });
  window.addEventListener('resize', hideHoverCard);
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && billModal.classList.contains('open')) {
      closeBillModal();
    }
    if (event.key === 'Escape' && hoverCard.classList.contains('open')) {
      hideHoverCard();
    }
  });
  resetFiltersButton.addEventListener('click', resetFilters);

  // Column resize functionality
  (function initColumnResize() {
    const table = document.querySelector('.bills-table');
    if (!table) return;

    let isResizing = false;
    let currentTh = null;
    let startX = 0;
    let startWidth = 0;
    let nextTh = null;
    let nextStartWidth = 0;

    function onMouseDown(e) {
      const handle = e.target.closest('.resize-handle');
      if (!handle) return;

      e.preventDefault();
      e.stopPropagation();

      currentTh = handle.parentElement;
      nextTh = currentTh.nextElementSibling;
      isResizing = true;
      startX = e.pageX;
      startWidth = currentTh.offsetWidth;
      if (nextTh) {
        nextStartWidth = nextTh.offsetWidth;
      }

      handle.classList.add('resizing');
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    }

    function onMouseMove(e) {
      if (!isResizing || !currentTh) return;

      const diff = e.pageX - startX;
      const newWidth = startWidth + diff;
      const minWidth = 60;

      if (newWidth >= minWidth) {
        currentTh.style.width = `${newWidth}px`;
        if (nextTh && nextStartWidth - diff >= minWidth) {
          nextTh.style.width = `${nextStartWidth - diff}px`;
        }
      }
    }

    function onMouseUp() {
      if (!isResizing) return;

      isResizing = false;
      if (currentTh) {
        const handle = currentTh.querySelector('.resize-handle');
        if (handle) handle.classList.remove('resizing');
      }
      currentTh = null;
      nextTh = null;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    }

    table.addEventListener('mousedown', onMouseDown);
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  })();

  // Font size button handlers for each column
  document.querySelectorAll('.font-size-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const column = btn.dataset.column;
      const action = btn.dataset.action;
      if (column && action) {
        if (action === 'up') {
          increaseColumnFontSize(column);
        } else if (action === 'down') {
          decreaseColumnFontSize(column);
        }
      }
    });
  });

  // Sortable header click handlers
  document.querySelectorAll('.bills-table th.sortable').forEach((th) => {
    th.addEventListener('click', () => {
      const column = th.dataset.sort;
      if (column) {
        cycleSort(column);
      }
    });
    th.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        const column = th.dataset.sort;
        if (column) {
          cycleSort(column);
        }
      }
    });
  });

  loadColumnFontSizes();
  loadBills();
