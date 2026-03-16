const DATA_URL = './data/city_council_testimony.json';
const FILTERS_STORAGE_KEY = 'cityCouncilTestimonyFiltersV1';

const billsTableBody = document.getElementById('bills-table-body');
const billFilterInput = document.getElementById('bill-filter');
const sponsorFilterInput = document.getElementById('sponsor-filter');
const categoryFilterInput = document.getElementById('category-filter');
const upcomingOnlyToggle = document.getElementById('upcoming-only-toggle');
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
const billsTable = document.querySelector('.bills-table');
const billsTableWrap = document.querySelector('.bills-table-wrap');
const insightsGrid = document.querySelector('.insights-grid');

let allBills = [];
let preparedBills = [];
let activeSponsor = '';
let activeCategory = '';
let sortColumn = '';
let sortDirection = '';
let showUpcomingOnly = true;
let hoverSwapTimer = null;
let sponsorProfiles = new Map();
let resizeState = null;
let gridResizeState = null;

const GRID_WIDTHS_STORAGE_KEY = 'cityCouncilGridWidthsV1';

const COLUMN_FONT_SIZE_CONFIG = {
  sponsor: { min: 12, max: 22, step: 1, default: 16, storageKey: 'cityCouncilFontSizeSponsor' },
  category: { min: 12, max: 22, step: 1, default: 16, storageKey: 'cityCouncilFontSizeCategory' },
  bills: { min: 12, max: 22, step: 1, default: 16, storageKey: 'cityCouncilFontSizeBills' }
};

const columnFontSizes = {
  sponsor: COLUMN_FONT_SIZE_CONFIG.sponsor.default,
  category: COLUMN_FONT_SIZE_CONFIG.category.default,
  bills: COLUMN_FONT_SIZE_CONFIG.bills.default
};

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function normalizePersonName(value) {
  return String(value || '')
    .toLowerCase()
    .replace(/\b(council vice-president|council vice president|vice president|council president|city council member|council member)\b/g, '')
    .replace(/,\s*district\s+\d+.*/g, '')
    .replace(/["“”]/g, '')
    .replace(/[^a-z0-9\s'-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function truncateText(text, maxLength) {
  const normalized = String(text || '').replace(/\s+/g, ' ').trim();
  if (!normalized || normalized.length <= maxLength) {
    return normalized;
  }
  return `${normalized.slice(0, Math.max(0, maxLength - 1)).trimEnd()}…`;
}

function getSponsorProfile(name) {
  const normalized = normalizePersonName(name);
  if (!normalized) {
    return null;
  }
  if (sponsorProfiles.has(normalized)) {
    return sponsorProfiles.get(normalized);
  }
  const tokens = normalized.split(' ');
  if (tokens.length >= 2) {
    return sponsorProfiles.get(`${tokens[0]} ${tokens[tokens.length - 1]}`) || null;
  }
  return null;
}

function buildProfileImageMarkup(profile, caption = 'Official portrait') {
  if (!profile?.portrait_path) {
    return '';
  }
  return `
    <section class="hover-card-images">
      <figure>
        <img alt="${escapeHtml(profile.name || 'Official portrait')}" src="${escapeHtml(profile.portrait_path)}">
        <figcaption>${escapeHtml(caption)}</figcaption>
      </figure>
    </section>
  `;
}

function syncBillsDisplayFontSize() {
  document.documentElement.style.setProperty('--bills-font-size', `${columnFontSizes.bills}px`);
}

function loadColumnFontSizes() {
  for (const [column, config] of Object.entries(COLUMN_FONT_SIZE_CONFIG)) {
    try {
      const saved = localStorage.getItem(config.storageKey);
      if (!saved) {
        continue;
      }
      const parsed = parseInt(saved, 10);
      if (!Number.isNaN(parsed) && parsed >= config.min && parsed <= config.max) {
        columnFontSizes[column] = parsed;
      }
    } catch {
      // Ignore storage errors.
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

function adjustColumnFontSize(column, direction) {
  const config = COLUMN_FONT_SIZE_CONFIG[column];
  if (!config) {
    return;
  }
  const nextValue = columnFontSizes[column] + (direction * config.step);
  columnFontSizes[column] = Math.max(config.min, Math.min(config.max, nextValue));
  const element = document.getElementById(`${column}-column`);
  if (element) {
    element.style.setProperty('--column-font-size', `${columnFontSizes[column]}px`);
  }
  if (column === 'bills') {
    syncBillsDisplayFontSize();
  }
  try {
    localStorage.setItem(config.storageKey, String(columnFontSizes[column]));
  } catch {
    // Ignore storage errors.
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
        category: '',
        upcomingOnly: true
      };
    }
    const parsed = JSON.parse(raw);
    return {
      billQuery: String(parsed.billQuery || ''),
      sponsorQuery: String(parsed.sponsorQuery || ''),
      categoryQuery: String(parsed.categoryQuery || ''),
      sponsor: String(parsed.sponsor || ''),
      category: String(parsed.category || ''),
      upcomingOnly: parsed.upcomingOnly !== false
    };
  } catch {
    return {
      billQuery: '',
      sponsorQuery: '',
      categoryQuery: '',
      sponsor: '',
      category: '',
      upcomingOnly: true
    };
  }
}

function persistFilters() {
  try {
    localStorage.setItem(FILTERS_STORAGE_KEY, JSON.stringify({
      billQuery: billFilterInput.value || '',
      sponsorQuery: sponsorFilterInput.value || '',
      categoryQuery: categoryFilterInput.value || '',
      sponsor: activeSponsor,
      category: activeCategory,
      upcomingOnly: showUpcomingOnly
    }));
  } catch {
    // Ignore storage errors.
  }
}

function clearPersistedFilters() {
  try {
    localStorage.removeItem(FILTERS_STORAGE_KEY);
  } catch {
    // Ignore storage errors.
  }
}

function loadPersistedGridWidths() {
  try {
    const raw = localStorage.getItem(GRID_WIDTHS_STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed) || parsed.length !== 3) {
      return null;
    }
    return parsed.map((value) => Number(value)).filter((value) => Number.isFinite(value));
  } catch {
    return null;
  }
}

function persistGridWidths(widths) {
  try {
    localStorage.setItem(GRID_WIDTHS_STORAGE_KEY, JSON.stringify(widths.map((value) => Math.round(value))));
  } catch {
    // Ignore storage errors.
  }
}

function updateSearchClearButtons() {
  for (const button of searchClearButtons) {
    const target = document.getElementById(button.dataset.clearTarget || '');
    const targetId = button.dataset.clearTarget || '';
    const hasText = Boolean(target && target.value.trim());
    const hasSelection = (
      (targetId === 'sponsor-filter' && Boolean(activeSponsor))
      || (targetId === 'category-filter' && Boolean(activeCategory))
    );
    button.classList.toggle('visible', hasText || hasSelection);
  }
}

function formatDateTime(dateValue, timeValue = '') {
  const combined = [dateValue, timeValue].filter(Boolean).join(' ');
  if (!combined) {
    return '';
  }
  const parsed = new Date(combined);
  if (Number.isNaN(parsed.getTime())) {
    return combined;
  }
  return parsed.toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: timeValue ? 'short' : undefined
  });
}

function getHearingDate(record) {
  if (!record.meeting_date) {
    return null;
  }
  const parsed = new Date([record.meeting_date, record.meeting_time || ''].filter(Boolean).join(' '));
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function isUpcomingBill(record) {
  const hearingDate = getHearingDate(record);
  if (!hearingDate) {
    return false;
  }
  const now = new Date();
  return hearingDate.getTime() >= new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
}

function extractCategories(record) {
  const values = Array.isArray(record.categories) ? record.categories : [];
  return [...new Set(values.map((value) => String(value || '').trim()).filter(Boolean))];
}

function searchableText(record) {
  const attachmentNames = (record.attachments || []).map((item) => item.name);
  return [
    record.file_number,
    record.title,
    record.summary,
    record.status,
    record.type,
    record.committee,
    record.meeting_name,
    record.primary_sponsor,
    ...(record.sponsors || []),
    ...extractCategories(record),
    record.latest_action,
    ...(record.history || []),
    ...attachmentNames
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
}

function buildPreparedBills(records) {
  return records.map((bill, index) => ({
    index,
    bill,
    sponsor: String(bill.primary_sponsor || 'No listed sponsor').trim() || 'No listed sponsor',
    categories: extractCategories(bill),
    searchText: searchableText(bill),
    hearingDate: getHearingDate(bill)
  }));
}

function renderSponsorTable() {
  const sponsorQuery = sponsorFilterInput.value.trim().toLowerCase();
  const counts = new Map();

  for (const bill of allBills) {
    const sponsor = String(bill.primary_sponsor || 'No listed sponsor').trim() || 'No listed sponsor';
    counts.set(sponsor, (counts.get(sponsor) || 0) + 1);
  }

  const rows = [...counts.entries()]
    .filter(([name]) => !sponsorQuery || name.toLowerCase().includes(sponsorQuery))
    .sort((a, b) => (b[1] - a[1]) || a[0].localeCompare(b[0]))
    .map(([name, count]) => `
      <div class="list-row">
        <button type="button" class="sponsor-button${name === activeSponsor ? ' active' : ''}" data-sponsor="${escapeHtml(name)}">
          ${escapeHtml(name)}
        </button>
        <span class="list-count">${count.toLocaleString()}</span>
      </div>
    `)
    .join('');

  sponsorTableBody.innerHTML = rows || '<div class="list-row"><span>No sponsor data available.</span><span class="list-count">0</span></div>';
}

function renderCategoryTable() {
  const categoryQuery = categoryFilterInput.value.trim().toLowerCase();
  const categoryCounts = new Map();

  for (const entry of preparedBills) {
    if (activeSponsor && entry.sponsor !== activeSponsor) {
      continue;
    }
    const categories = entry.categories.length ? entry.categories : ['Uncategorized'];
    for (const category of categories) {
      categoryCounts.set(category, (categoryCounts.get(category) || 0) + 1);
    }
  }

  if (activeCategory && !categoryCounts.has(activeCategory)) {
    activeCategory = '';
  }

  const rows = [...categoryCounts.entries()]
    .filter(([name]) => !categoryQuery || name.toLowerCase().includes(categoryQuery))
    .sort((a, b) => (b[1] - a[1]) || a[0].localeCompare(b[0]))
    .map(([name, count]) => `
      <div class="list-row">
        <button type="button" class="sponsor-button${name === activeCategory ? ' active' : ''}" data-category="${escapeHtml(name)}">
          ${escapeHtml(name)}
        </button>
        <span class="list-count">${count.toLocaleString()}</span>
      </div>
    `)
    .join('');

  categoryTableBody.innerHTML = rows || '<div class="list-row"><span>No category data available.</span><span class="list-count">0</span></div>';
}

function getFilteredEntries() {
  const query = billFilterInput.value.trim().toLowerCase();
  return preparedBills
    .filter((entry) => !showUpcomingOnly || isUpcomingBill(entry.bill))
    .filter((entry) => !activeSponsor || entry.sponsor === activeSponsor)
    .filter((entry) => !activeCategory || (entry.categories.length ? entry.categories : ['Uncategorized']).includes(activeCategory))
    .filter((entry) => !query || entry.searchText.includes(query));
}

function getSortValue(entry, column) {
  switch (column) {
    case 'billNumber':
      return String(entry.bill.file_number || '').toLowerCase();
    case 'title':
      return String(entry.bill.title || '').toLowerCase();
    case 'sponsor':
      return String(entry.bill.primary_sponsor || '').toLowerCase();
    case 'status':
      return String(entry.bill.status || '').toLowerCase();
    case 'hearingDate':
      return entry.hearingDate ? entry.hearingDate.getTime() : Number.MAX_SAFE_INTEGER;
    default:
      return String(entry.bill.title || '').toLowerCase();
  }
}

function sortEntries(entries) {
  if (!sortColumn || !sortDirection) {
    return [...entries];
  }
  return [...entries].sort((a, b) => {
    const left = getSortValue(a, sortColumn);
    const right = getSortValue(b, sortColumn);
    if (left === right) {
      return String(a.bill.file_number || a.bill.title || '').localeCompare(String(b.bill.file_number || b.bill.title || ''));
    }
    if (typeof left === 'number' && typeof right === 'number') {
      return sortDirection === 'asc' ? left - right : right - left;
    }
    return sortDirection === 'asc'
      ? String(left).localeCompare(String(right))
      : String(right).localeCompare(String(left));
  });
}

function createBillRowMarkup(entry) {
  const { bill, index } = entry;
  const sponsor = String(bill.primary_sponsor || 'No listed sponsor').trim() || 'No listed sponsor';
  const hearingLabel = formatDateTime(bill.meeting_date, bill.meeting_time);
  return `
    <tr>
      <td class="bill-number-cell">${escapeHtml(bill.file_number || 'N/A')}</td>
      <td>
        <p class="bill-title">
          <button type="button" class="bill-title-button" data-bill-index="${index}">
            ${escapeHtml(bill.title || 'Untitled item')}
          </button>
        </p>
      </td>
      <td>
        <button type="button" class="bill-sponsor-button" data-sponsor-name="${escapeHtml(sponsor)}">
          ${escapeHtml(sponsor)}
        </button>
      </td>
      <td>${escapeHtml(bill.status || 'Status unavailable')}</td>
      <td>${escapeHtml(hearingLabel || 'No hearing listed')}</td>
    </tr>
  `;
}

function renderBills() {
  const filteredEntries = sortEntries(getFilteredEntries());
  billsTableBody.innerHTML = filteredEntries.map(createBillRowMarkup).join('')
    || '<tr><td colspan="5">No City Council testimony records matched these filters.</td></tr>';

  const testimonyCount = filteredEntries.filter((entry) => entry.bill.has_testimony).length;
  billCount.textContent = `${filteredEntries.length.toLocaleString()} records`;
  statusMessage.textContent = testimonyCount
    ? `${testimonyCount.toLocaleString()} records include testimony or comment attachments.`
    : 'No testimony or comment attachments in the current filtered set.';
}

function updateSortIndicators() {
  for (const header of document.querySelectorAll('th.sortable')) {
    header.classList.remove('sort-asc', 'sort-desc');
    if (header.dataset.sort === sortColumn) {
      header.classList.add(sortDirection === 'asc' ? 'sort-asc' : 'sort-desc');
    }
  }
}

function stringifyValue(value) {
  if (value === null || value === undefined || value === '') {
    return 'N/A';
  }
  if (Array.isArray(value)) {
    return value.length ? value.join(', ') : 'N/A';
  }
  return String(value);
}

function renderLinks(items) {
  if (!items || !items.length) {
    return 'N/A';
  }
  return items.map((item) => {
    const label = item.name || item.label || item.url;
    return `<a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}</a>`;
  }).join('<br>');
}

function renderBillModal(bill) {
  const sponsorProfile = bill.primary_sponsor_profile || getSponsorProfile(bill.primary_sponsor);
  const fields = [
    ['File Number', bill.file_number],
    ['Title', bill.title],
    ['Summary', bill.summary],
    ['Status', bill.status],
    ['Type', bill.type],
    ['Committee / Meeting', bill.meeting_name || bill.committee],
    ['Hearing', formatDateTime(bill.meeting_date, bill.meeting_time)],
    ['Location', bill.meeting_location],
    ['Primary Sponsor', bill.primary_sponsor],
    ['Sponsor Bio', sponsorProfile?.biography ? truncateText(sponsorProfile.biography, 1200) : ''],
    ['All Sponsors', bill.sponsors],
    ['Categories', bill.categories],
    ['Latest Action', bill.latest_action],
    ['History', bill.history]
  ];

  billModalTitle.textContent = bill.file_number
    ? `${bill.file_number} Details`
    : 'Record Details';
  billModalContent.innerHTML = `
    ${buildProfileImageMarkup(sponsorProfile)}
    <table class="bill-detail-table">
      <tbody>
        ${fields.map(([label, value]) => `
          <tr>
            <th>${escapeHtml(label)}</th>
            <td>${escapeHtml(stringifyValue(value))}</td>
          </tr>
        `).join('')}
        <tr>
          <th>Meeting Link</th>
          <td>${bill.meeting_url ? `<a href="${escapeHtml(bill.meeting_url)}" target="_blank" rel="noopener noreferrer">Open meeting page</a>` : 'N/A'}</td>
        </tr>
        <tr>
          <th>Legislation Link</th>
          <td>${bill.detail_url ? `<a href="${escapeHtml(bill.detail_url)}" target="_blank" rel="noopener noreferrer">Open legislation page</a>` : 'N/A'}</td>
        </tr>
        <tr>
          <th>Sponsor Bio Page</th>
          <td>${sponsorProfile?.bio_url ? `<a href="${escapeHtml(sponsorProfile.bio_url)}" target="_blank" rel="noopener noreferrer">Open official bio</a>` : 'N/A'}</td>
        </tr>
        <tr>
          <th>Testimony / Comment</th>
          <td>${renderLinks(bill.testimony_attachments)}</td>
        </tr>
        <tr>
          <th>All Attachments</th>
          <td>${renderLinks(bill.attachments)}</td>
        </tr>
      </tbody>
    </table>
  `;
}

function openBillModal(bill) {
  renderBillModal(bill);
  billModal.classList.add('open');
  billModalClose.focus();
}

function closeBillModal() {
  billModal.classList.remove('open');
}

function buildSponsorHoverMarkup(name) {
  const entries = preparedBills.filter((entry) => entry.sponsor === name);
  const testimonyCount = entries.filter((entry) => entry.bill.has_testimony).length;
  const committees = [...new Set(entries.map((entry) => entry.bill.committee).filter(Boolean))].slice(0, 6);
  const profile = getSponsorProfile(name);
  return `
    <p class="hover-card-kicker">Lead Sponsor</p>
    <h3>${escapeHtml(name)}</h3>
    <p class="hover-card-meta">Records: ${entries.length.toLocaleString()}</p>
    <p class="hover-card-meta">With testimony: ${testimonyCount.toLocaleString()}</p>
    ${committees.length ? `<p class="hover-card-meta">Committees: ${escapeHtml(committees.join(' | '))}</p>` : ''}
    ${profile?.biography ? `<p>${escapeHtml(truncateText(profile.biography, 420))}</p>` : ''}
    ${profile?.bio_url ? `<p class="hover-card-meta"><a href="${escapeHtml(profile.bio_url)}" target="_blank" rel="noopener noreferrer">Official bio</a></p>` : ''}
    ${buildProfileImageMarkup(profile)}
  `;
}

function buildCategoryHoverMarkup(name) {
  const entries = preparedBills.filter((entry) => (entry.categories.length ? entry.categories : ['Uncategorized']).includes(name));
  const items = entries.slice(0, 6).map((entry) => ({
    fileNumber: entry.bill.file_number || 'N/A',
    title: entry.bill.title || 'Untitled item',
    hearing: formatDateTime(entry.bill.meeting_date, entry.bill.meeting_time) || 'No hearing listed'
  }));
  return `
    <p class="hover-card-kicker">Category</p>
    <h3>${escapeHtml(name)}</h3>
    <p class="hover-card-meta">Records: ${entries.length.toLocaleString()}</p>
    ${items.length ? `
      <p class="hover-card-meta hover-card-meta-accent">Sample items</p>
      <ul class="hover-card-list">
        ${items.map((item) => `
          <li>
            <span class="hover-card-list-file">${escapeHtml(item.fileNumber)}</span>
            <span class="hover-card-list-title">${escapeHtml(item.title)}</span>
            <span class="hover-card-list-meta">${escapeHtml(item.hearing)}</span>
          </li>
        `).join('')}
      </ul>
    ` : ''}
  `;
}

function buildBillHoverMarkup(bill) {
  const hearingLabel = formatDateTime(bill.meeting_date, bill.meeting_time) || 'No hearing listed';
  const testimony = (bill.testimony_attachments || []).map((item) => item.name).slice(0, 3);
  const sponsorProfile = bill.primary_sponsor_profile || getSponsorProfile(bill.primary_sponsor);
  return `
    <p class="hover-card-kicker">Council Item</p>
    <h3>${escapeHtml(bill.file_number || 'N/A')} ${escapeHtml(bill.title || '')}</h3>
    <p class="hover-card-meta">Sponsor: ${escapeHtml(bill.primary_sponsor || 'No listed sponsor')}</p>
    <p class="hover-card-meta">Status: ${escapeHtml(bill.status || 'Status unavailable')}</p>
    <p class="hover-card-meta">Hearing: ${escapeHtml(hearingLabel)}</p>
    ${sponsorProfile?.biography ? `<p>${escapeHtml(truncateText(sponsorProfile.biography, 260))}</p>` : ''}
    ${testimony.length ? `<p class="hover-card-meta hover-card-meta-accent">Testimony: ${escapeHtml(testimony.join(' | '))}</p>` : ''}
    ${buildProfileImageMarkup(sponsorProfile)}
  `;
}

function positionHoverCard(clientX, clientY) {
  const rect = hoverCard.getBoundingClientRect();
  let left = clientX + 12;
  let top = clientY + 12;
  if (left + rect.width > window.innerWidth - 8) {
    left = clientX - rect.width - 12;
  }
  if (top + rect.height > window.innerHeight - 8) {
    top = clientY - rect.height - 12;
  }
  hoverCard.style.left = `${Math.max(8, left)}px`;
  hoverCard.style.top = `${Math.max(8, top)}px`;
}

function positionLeftOverlayCard() {
  const left = 10;
  const top = 84;
  const height = Math.max(220, window.innerHeight - top - 10);
  hoverCard.style.left = `${left}px`;
  hoverCard.style.top = `${top}px`;
  hoverCard.style.height = `${height}px`;
  hoverCard.style.maxHeight = `${height}px`;
}

function positionRightOverlayCard() {
  const top = 84;
  const gap = 10;
  const width = Math.min(Math.max(window.innerWidth * 0.5, 380), 760);
  const left = Math.max(10, window.innerWidth - width - gap);
  const height = Math.max(220, window.innerHeight - top - 10);
  hoverCard.style.left = `${left}px`;
  hoverCard.style.top = `${top}px`;
  hoverCard.style.height = `${height}px`;
  hoverCard.style.maxHeight = `${height}px`;
}

function showHoverCard(markup, clientX, clientY) {
  const nextMarkup = `<div class="hover-card-content">${markup}</div>`;
  if (hoverCard.classList.contains('open') && hoverCard.innerHTML !== nextMarkup) {
    window.clearTimeout(hoverSwapTimer);
    const preserveLeftOverlay = hoverCard.classList.contains('left-overlay');
    const preserveRightOverlay = hoverCard.classList.contains('right-overlay');
    hoverCard.classList.add('is-swapping');
    hoverSwapTimer = window.setTimeout(() => {
      hoverCard.innerHTML = nextMarkup;
      hoverCard.classList.remove('is-swapping');
      if (preserveLeftOverlay) {
        hoverCard.classList.add('left-overlay');
        hoverCard.classList.remove('right-overlay');
        positionLeftOverlayCard();
      } else if (preserveRightOverlay) {
        hoverCard.classList.add('right-overlay');
        hoverCard.classList.remove('left-overlay');
        positionRightOverlayCard();
      } else {
        positionHoverCard(clientX, clientY);
      }
    }, 60);
  } else {
    hoverCard.innerHTML = nextMarkup;
    hoverCard.classList.remove('left-overlay', 'right-overlay');
    hoverCard.style.height = '';
    hoverCard.style.maxHeight = '';
  }
  hoverCard.classList.add('open');
  hoverCard.setAttribute('aria-hidden', 'false');
  if (!hoverCard.classList.contains('left-overlay') && !hoverCard.classList.contains('right-overlay')) {
    positionHoverCard(clientX, clientY);
  }
}

function showSponsorHover(name, side = 'right') {
  showHoverCard(buildSponsorHoverMarkup(name), 14, 120);
  if (side === 'left') {
    hoverCard.classList.add('left-overlay');
    positionLeftOverlayCard();
    return;
  }
  hoverCard.classList.add('right-overlay');
  positionRightOverlayCard();
}

function showCategoryHover(name) {
  showHoverCard(buildCategoryHoverMarkup(name), 14, 120);
  hoverCard.classList.add('right-overlay');
  positionRightOverlayCard();
}

function showBillHover(bill) {
  showHoverCard(buildBillHoverMarkup(bill), 14, 120);
  hoverCard.classList.add('left-overlay');
  positionLeftOverlayCard();
}

function hideHoverCard() {
  window.clearTimeout(hoverSwapTimer);
  hoverCard.classList.remove('open', 'is-swapping', 'left-overlay', 'right-overlay');
  hoverCard.style.height = '';
  hoverCard.style.maxHeight = '';
  hoverCard.setAttribute('aria-hidden', 'true');
}

function pointerLeftElement(event, selector) {
  const current = event.target.closest(selector);
  if (!current) {
    return false;
  }
  const related = event.relatedTarget;
  return !related || !current.contains(related);
}

function updateActiveSponsor(nextSponsor) {
  activeSponsor = activeSponsor === nextSponsor ? '' : nextSponsor;
  renderSponsorTable();
  renderCategoryTable();
  renderBills();
  persistFilters();
  updateSearchClearButtons();
}

function updateActiveCategory(nextCategory) {
  activeCategory = activeCategory === nextCategory ? '' : nextCategory;
  renderCategoryTable();
  renderBills();
  persistFilters();
  updateSearchClearButtons();
}

function resetFilters() {
  billFilterInput.value = '';
  sponsorFilterInput.value = '';
  categoryFilterInput.value = '';
  activeSponsor = '';
  activeCategory = '';
  showUpcomingOnly = true;
  upcomingOnlyToggle.checked = true;
  clearPersistedFilters();
  updateSearchClearButtons();
  renderSponsorTable();
  renderCategoryTable();
  renderBills();
}

async function loadData() {
  const response = await fetch(DATA_URL, { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`Failed to load ${DATA_URL}: ${response.status}`);
  }
  return response.json();
}

function applyPersistedState(records, payload) {
  allBills = records;
  preparedBills = buildPreparedBills(records);
  sponsorProfiles = new Map();
  for (const profile of (Array.isArray(payload.sponsor_profiles) ? payload.sponsor_profiles : [])) {
    const normalized = normalizePersonName(profile.name);
    if (normalized) {
      sponsorProfiles.set(normalized, profile);
      const tokens = normalized.split(' ');
      if (tokens.length >= 2) {
        sponsorProfiles.set(`${tokens[0]} ${tokens[tokens.length - 1]}`, profile);
      }
    }
  }

  const persisted = loadPersistedFilters();
  billFilterInput.value = persisted.billQuery;
  sponsorFilterInput.value = persisted.sponsorQuery;
  categoryFilterInput.value = persisted.categoryQuery;
  activeSponsor = persisted.sponsor;
  activeCategory = persisted.category;
  showUpcomingOnly = persisted.upcomingOnly;
  upcomingOnlyToggle.checked = showUpcomingOnly;

  const sponsorSet = new Set(preparedBills.map((entry) => entry.sponsor));
  if (activeSponsor && !sponsorSet.has(activeSponsor)) {
    activeSponsor = '';
  }

  billUpdated.textContent = payload.fetched_at
    ? `Updated ${formatDateTime(payload.fetched_at)}`
    : '';

  renderSponsorTable();
  renderCategoryTable();
  renderBills();
  updateSortIndicators();
  updateSearchClearButtons();
}

function getGridPanels() {
  return [
    document.getElementById('sponsor-column'),
    document.getElementById('category-column'),
    document.getElementById('bills-column')
  ];
}

function applyGridWidths(widths) {
  if (!insightsGrid || window.innerWidth <= 700 || !Array.isArray(widths) || widths.length !== 3) {
    return;
  }
  insightsGrid.style.gridTemplateColumns = [
    `${Math.round(widths[0])}px`,
    '14px',
    `${Math.round(widths[1])}px`,
    '14px',
    `${Math.round(widths[2])}px`
  ].join(' ');
}

function syncGridWidthsFromLayout() {
  if (!insightsGrid || window.innerWidth <= 700) {
    return;
  }
  const panels = getGridPanels();
  if (panels.some((panel) => !panel)) {
    return;
  }
  const widths = panels.map((panel) => panel.getBoundingClientRect().width);
  applyGridWidths(widths);
}

function initializeGridWidths() {
  if (!insightsGrid) {
    return;
  }
  if (window.innerWidth <= 700) {
    insightsGrid.style.gridTemplateColumns = '';
    return;
  }
  const persisted = loadPersistedGridWidths();
  if (persisted && persisted.length === 3) {
    applyGridWidths(persisted);
  } else {
    syncGridWidthsFromLayout();
  }
}

function stopGridResize() {
  if (!gridResizeState) {
    return;
  }
  gridResizeState.handle.classList.remove('resizing');
  document.body.classList.remove('is-resizing-columns');
  window.removeEventListener('mousemove', handleGridResizeMove);
  window.removeEventListener('mouseup', stopGridResize);
  persistGridWidths(gridResizeState.widths);
  gridResizeState = null;
}

function handleGridResizeMove(event) {
  if (!gridResizeState) {
    return;
  }
  const delta = event.clientX - gridResizeState.startX;
  const nextWidths = [...gridResizeState.startWidths];
  const leftIndex = gridResizeState.leftIndex;
  const rightIndex = gridResizeState.rightIndex;
  const proposedLeft = gridResizeState.startWidths[leftIndex] + delta;
  const proposedRight = gridResizeState.startWidths[rightIndex] - delta;
  nextWidths[leftIndex] = Math.max(gridResizeState.minWidth, proposedLeft);
  nextWidths[rightIndex] = Math.max(gridResizeState.minWidth, proposedRight);

  const totalPair = gridResizeState.startWidths[leftIndex] + gridResizeState.startWidths[rightIndex];
  if (nextWidths[leftIndex] + nextWidths[rightIndex] !== totalPair) {
    if (nextWidths[leftIndex] === gridResizeState.minWidth) {
      nextWidths[rightIndex] = totalPair - nextWidths[leftIndex];
    } else if (nextWidths[rightIndex] === gridResizeState.minWidth) {
      nextWidths[leftIndex] = totalPair - nextWidths[rightIndex];
    }
  }

  gridResizeState.widths = nextWidths;
  applyGridWidths(nextWidths);
}

function startGridResize(event) {
  const handle = event.target.closest('[data-grid-resize]');
  if (!handle || !insightsGrid || window.innerWidth <= 700) {
    return;
  }
  event.preventDefault();
  const currentWidths = getGridPanels().map((panel) => panel.getBoundingClientRect().width);
  const leftIndex = handle.dataset.gridResize === 'sponsor' ? 0 : 1;
  const rightIndex = leftIndex + 1;
  gridResizeState = {
    handle,
    startX: event.clientX,
    startWidths: currentWidths,
    widths: currentWidths,
    leftIndex,
    rightIndex,
    minWidth: 220
  };
  handle.classList.add('resizing');
  document.body.classList.add('is-resizing-columns');
  window.addEventListener('mousemove', handleGridResizeMove);
  window.addEventListener('mouseup', stopGridResize);
}

function getResizableHeaders() {
  return [...document.querySelectorAll('.bills-table th.resizable')];
}

function syncTableColumnWidths() {
  if (!billsTable || !billsTableWrap) {
    return;
  }
  const headers = getResizableHeaders();
  if (!headers.length) {
    return;
  }
  const widths = headers.map((header) => header.getBoundingClientRect().width);
  headers.forEach((header, index) => {
    header.style.width = `${Math.round(widths[index])}px`;
  });
  const totalWidth = widths.reduce((sum, width) => sum + width, 0);
  const wrapWidth = billsTableWrap.getBoundingClientRect().width;
  billsTable.style.width = `${Math.round(Math.max(totalWidth, wrapWidth))}px`;
  billsTable.style.minWidth = '100%';
}

function stopColumnResize() {
  if (!resizeState) {
    return;
  }
  resizeState.handle.classList.remove('resizing');
  document.body.classList.remove('is-resizing-columns');
  window.removeEventListener('mousemove', handleColumnResizeMove);
  window.removeEventListener('mouseup', stopColumnResize);
  resizeState = null;
}

function handleColumnResizeMove(event) {
  if (!resizeState || !billsTable || !billsTableWrap) {
    return;
  }
  const delta = event.clientX - resizeState.startX;
  const nextPrimaryWidth = Math.max(
    resizeState.minPrimaryWidth,
    Math.min(resizeState.maxPrimaryWidth, resizeState.startPrimaryWidth + delta)
  );
  const nextSecondaryWidth = resizeState.combinedWidth - nextPrimaryWidth;
  resizeState.primaryHeader.style.width = `${Math.round(nextPrimaryWidth)}px`;
  resizeState.secondaryHeader.style.width = `${Math.round(nextSecondaryWidth)}px`;
  billsTable.style.width = `${Math.round(resizeState.tableWidth)}px`;
  billsTable.style.minWidth = '100%';
}

function startColumnResize(event) {
  const handle = event.target.closest('.resize-handle');
  if (!handle || !billsTable || !billsTableWrap) {
    return;
  }
  event.preventDefault();
  event.stopPropagation();
  const header = handle.closest('th');
  if (!header) {
    return;
  }
  syncTableColumnWidths();
  const headers = getResizableHeaders();
  const headerIndex = headers.indexOf(header);
  const nextHeader = headers[headerIndex + 1];
  if (!nextHeader) {
    return;
  }
  const primaryWidth = header.getBoundingClientRect().width;
  const secondaryWidth = nextHeader.getBoundingClientRect().width;
  const tableWidth = billsTableWrap.getBoundingClientRect().width;
  const minPrimaryWidth = Math.max(90, Math.min(primaryWidth, 120));
  const minSecondaryWidth = Math.max(90, Math.min(secondaryWidth, 120));
  resizeState = {
    handle,
    primaryHeader: header,
    secondaryHeader: nextHeader,
    startX: event.clientX,
    startPrimaryWidth: primaryWidth,
    combinedWidth: primaryWidth + secondaryWidth,
    minPrimaryWidth,
    maxPrimaryWidth: (primaryWidth + secondaryWidth) - minSecondaryWidth,
    tableWidth
  };
  handle.classList.add('resizing');
  document.body.classList.add('is-resizing-columns');
  window.addEventListener('mousemove', handleColumnResizeMove);
  window.addEventListener('mouseup', stopColumnResize);
}

async function init() {
  loadColumnFontSizes();
  initializeGridWidths();
  try {
    const payload = await loadData();
    const records = Array.isArray(payload.records) ? payload.records : [];
    applyPersistedState(records, payload);
  } catch (error) {
    console.error(error);
    billCount.textContent = 'No records loaded';
    statusMessage.textContent = 'Unable to load City Council testimony data.';
    billsTableBody.innerHTML = '<tr><td colspan="5">The local City Council testimony cache is missing or unreadable.</td></tr>';
  }
}

billFilterInput.addEventListener('input', () => {
  renderBills();
  persistFilters();
  updateSearchClearButtons();
});
sponsorFilterInput.addEventListener('input', () => {
  renderSponsorTable();
  persistFilters();
  updateSearchClearButtons();
});
categoryFilterInput.addEventListener('input', () => {
  renderCategoryTable();
  persistFilters();
  updateSearchClearButtons();
});
upcomingOnlyToggle.addEventListener('change', () => {
  showUpcomingOnly = upcomingOnlyToggle.checked;
  renderBills();
  persistFilters();
});
resetFiltersButton.addEventListener('click', resetFilters);

document.addEventListener('click', (event) => {
  const clearButton = event.target.closest('.search-clear');
  if (clearButton) {
    const targetId = clearButton.dataset.clearTarget || '';
    const target = document.getElementById(targetId);
    if (target) {
      target.value = '';
      if (targetId === 'sponsor-filter') {
        activeSponsor = '';
        renderSponsorTable();
        renderCategoryTable();
        renderBills();
        persistFilters();
      } else if (targetId === 'category-filter') {
        activeCategory = '';
        renderCategoryTable();
        renderBills();
        persistFilters();
      }
      target.dispatchEvent(new Event('input', { bubbles: true }));
      target.focus();
    }
  }
});

sponsorTableBody.addEventListener('click', (event) => {
  const button = event.target.closest('.sponsor-button');
  if (button) {
    updateActiveSponsor(button.dataset.sponsor || '');
  }
});

categoryTableBody.addEventListener('click', (event) => {
  const button = event.target.closest('.sponsor-button');
  if (button) {
    updateActiveCategory(button.dataset.category || '');
  }
});

billsTableBody.addEventListener('click', (event) => {
  const titleButton = event.target.closest('.bill-title-button');
  if (titleButton) {
    const entry = preparedBills[Number(titleButton.dataset.billIndex)];
    if (entry) {
      openBillModal(entry.bill);
    }
    return;
  }
  const sponsorButton = event.target.closest('.bill-sponsor-button');
  if (sponsorButton) {
    updateActiveSponsor(sponsorButton.dataset.sponsorName || '');
  }
});

for (const header of document.querySelectorAll('th.sortable')) {
  const applySort = () => {
    if (resizeState) {
      return;
    }
    const nextColumn = header.dataset.sort || 'title';
    if (sortColumn !== nextColumn) {
      sortColumn = nextColumn;
      sortDirection = 'asc';
    } else if (sortDirection === 'asc') {
      sortDirection = 'desc';
    } else if (sortDirection === 'desc') {
      sortColumn = '';
      sortDirection = '';
    } else {
      sortColumn = nextColumn;
      sortDirection = 'asc';
    }
    updateSortIndicators();
    renderBills();
  };
  header.addEventListener('click', applySort);
  header.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      applySort();
    }
  });
}

for (const handle of document.querySelectorAll('.resize-handle')) {
  handle.addEventListener('mousedown', startColumnResize);
}

for (const handle of document.querySelectorAll('[data-grid-resize]')) {
  handle.addEventListener('mousedown', startGridResize);
}

for (const button of document.querySelectorAll('.font-size-btn')) {
  button.addEventListener('click', () => {
    const column = button.dataset.column;
    const direction = button.dataset.action === 'up' ? 1 : -1;
    adjustColumnFontSize(column, direction);
  });
}

sponsorTableBody.addEventListener('mouseover', (event) => {
  const button = event.target.closest('.sponsor-button');
  if (button) {
    showSponsorHover(button.dataset.sponsor || '');
  }
});
sponsorTableBody.addEventListener('mouseout', (event) => {
  if (pointerLeftElement(event, '.sponsor-button')) {
    hideHoverCard();
  }
});
categoryTableBody.addEventListener('mouseover', (event) => {
  const button = event.target.closest('.sponsor-button');
  if (button) {
    showCategoryHover(button.dataset.category || '');
  }
});
categoryTableBody.addEventListener('mouseout', (event) => {
  if (pointerLeftElement(event, '.sponsor-button')) {
    hideHoverCard();
  }
});
billsTableBody.addEventListener('mouseover', (event) => {
  const sponsorButton = event.target.closest('.bill-sponsor-button');
  if (sponsorButton) {
    showSponsorHover(sponsorButton.dataset.sponsorName || '', 'left');
    return;
  }
  const rowButton = event.target.closest('.bill-title-button');
  if (!rowButton) {
    return;
  }
  const entry = preparedBills[Number(rowButton.dataset.billIndex)];
  if (entry) {
    showBillHover(entry.bill);
  }
});
billsTableBody.addEventListener('mouseout', (event) => {
  if (pointerLeftElement(event, '.bill-title-button') || pointerLeftElement(event, '.bill-sponsor-button')) {
    hideHoverCard();
  }
});
sponsorTableBody.addEventListener('mouseleave', hideHoverCard);
categoryTableBody.addEventListener('mouseleave', hideHoverCard);
billsTableBody.addEventListener('mouseleave', hideHoverCard);

window.addEventListener('resize', () => {
  initializeGridWidths();
  if (!hoverCard.classList.contains('open')) {
    return;
  }
  if (hoverCard.classList.contains('left-overlay')) {
    positionLeftOverlayCard();
  } else if (hoverCard.classList.contains('right-overlay')) {
    positionRightOverlayCard();
  }
});

billModalClose.addEventListener('click', closeBillModal);
billModal.addEventListener('click', (event) => {
  if (event.target === billModal) {
    closeBillModal();
  }
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') {
    hideHoverCard();
    closeBillModal();
  }
});

init();
