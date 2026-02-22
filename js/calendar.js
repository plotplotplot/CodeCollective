// Store all events globally
let allEvents = [];
let filteredEvents = [];
let rawEvents = [];
let eventGroups = new Set();
let calendar;
let currentView = 'dayGridMonth';
let isMobile = false;
let forceCardView = false;
let activeTagSlugs = new Set();
let calendarDisplayEvents = [];
const FEATURED_SOURCE_URL = 'https://luma.com/codecollective';

const LEGEND_PREFS_KEY = 'calendarLegendPrefs';
const CATEGORY_LABELS = [
  'Tech Skills',
  'Economic Development',
  'Infrastructure',
  'Makerspace',
  'Business',
  'Politics',
  'Finance',
  'Code Collective & Partners',
  'Other'
];

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

function getLegendPrefs(categories) {
  const defaultTags = Array.isArray(categories) ? categories.map(slugifyTag) : [];
  const defaults = {
    hidden: true,
    useTagColors: true,
    selectedTags: defaultTags
  };

  try {
    const stored = localStorage.getItem(LEGEND_PREFS_KEY);
    if (!stored) return defaults;
    const parsed = JSON.parse(stored);
    return {
      hidden: Boolean(parsed.hidden),
      useTagColors: parsed.useTagColors !== false,
      selectedTags: Array.isArray(parsed.selectedTags) ? parsed.selectedTags : defaultTags
    };
  } catch (error) {
    return defaults;
  }
}

function saveLegendPrefs() {
  const prefs = {
    hidden: document.body.classList.contains('legend-hidden'),
    useTagColors: !document.body.classList.contains('tags-disabled'),
    selectedTags: Array.from(activeTagSlugs)
  };
  try {
    localStorage.setItem(LEGEND_PREFS_KEY, JSON.stringify(prefs));
  } catch (error) {
    // Ignore storage failures silently.
  }
}

function buildLegend(categories) {
  const prefs = getLegendPrefs(categories);
  activeTagSlugs = new Set(prefs.selectedTags);

  const legendItems = document.getElementById('calendar-legend-items');
  if (!legendItems || !Array.isArray(categories)) {
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
      <span class="legend-text">Use tag colors</span>
    </label>
    <div class="legend-actions">
      <button type="button" class="legend-action" data-action="all">Select all</button>
      <button type="button" class="legend-action" data-action="none">Select none</button>
      <button type="button" class="legend-action" data-action="hide">Hide legend</button>
    </div>
  `;
  legendItems.appendChild(controls);

  const list = document.createElement('div');
  list.className = 'legend-list';
  categories.forEach(label => {
    const slug = slugifyTag(label);
    const isChecked = activeTagSlugs.size === 0 ? true : activeTagSlugs.has(slug);
    const item = document.createElement('label');
    item.className = 'legend-item';
    item.innerHTML = `
      <input type="checkbox" data-tag="${slug}" ${isChecked ? 'checked' : ''} />
      <span class="legend-swatch tag-${slug}"></span>
      <span class="legend-text">${label}</span>
    `;
    list.appendChild(item);
  });
  legendItems.appendChild(list);

  legendItems.addEventListener('change', event => {
    if (event.target.matches('#toggle-tag-formatting')) {
      setTagFormattingEnabled(event.target.checked);
      saveLegendPrefs();
      return;
    }
    if (!event.target.matches('input[type="checkbox"][data-tag]')) return;
    updateActiveTagsFromLegend();
    applyTagFilters();
  });

  legendItems.addEventListener('click', event => {
    const actionBtn = event.target.closest('.legend-action');
    if (!actionBtn) return;
    const action = actionBtn.dataset.action;
    if (action === 'all') {
      setLegendCheckboxes(true);
    } else if (action === 'none') {
      setLegendCheckboxes(false);
    } else if (action === 'hide') {
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

function setLegendCheckboxes(checked) {
  const inputs = document.querySelectorAll('#calendar-legend-items input[type="checkbox"][data-tag]');
  inputs.forEach(input => {
    input.checked = checked;
  });
  updateActiveTagsFromLegend();
  applyTagFilters();
}

function updateActiveTagsFromLegend() {
  const inputs = document.querySelectorAll('#calendar-legend-items input[type="checkbox"][data-tag]');
  activeTagSlugs = new Set(
    Array.from(inputs)
      .filter(input => input.checked)
      .map(input => input.dataset.tag)
  );
}

function eventMatchesTags(tags) {
  if (!activeTagSlugs || activeTagSlugs.size === 0) return false;
  const normalizedTags = Array.isArray(tags) ? tags.map(slugifyTag).filter(Boolean) : [];

  if (normalizedTags.length === 0) {
    return activeTagSlugs.has('other');
  }

  const matchesKnown = normalizedTags.some(tag => activeTagSlugs.has(tag));
  if (matchesKnown) return true;

  return activeTagSlugs.has('other');
}

function filterEventsByTags(events) {
  return events.filter(event => eventMatchesTags(event.extendedProps?.tags));
}

function filterRawEventsByTags(events) {
  return events.filter(event => eventMatchesTags(event.tags));
}

function applyTagFilters() {
  const tagFilteredEvents = filterEventsByTags(allEvents);
  calendarDisplayEvents = tagFilteredEvents;

  if (isMobile) {
    initializeMobileCards(tagFilteredEvents);
  } else if (calendar) {
    calendar.removeAllEvents();
    calendar.addEventSource(tagFilteredEvents);
    calendar.render();
  } else {
    initializeCalendar(tagFilteredEvents);
  }

  populateCodeCollectiveEvents(filterRawEventsByTags(rawEvents));
  saveLegendPrefs();
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

// Fetch and parse event data
document.addEventListener('DOMContentLoaded', function () {
  forceCardView = Boolean(window.FORCE_CALENDAR_CARDS);
  const stayOnCalendar = shouldStayOnCalendarView();
  const mobileViewport = isMobileDevice();
  isMobile = forceCardView ? true : (mobileViewport && !stayOnCalendar);

  if (!forceCardView && isMobile) {
    const query = window.location.search || '';
    const target = `/simplecalendar.html${query}`;
    window.location.replace(target);
    return;
  }

  const city = getCityFromUrl();
  const endpoint = `/${city}/upcoming_events.json`;

  fetch(endpoint)
    .then(response => {
      if (!response.ok) {
        throw new Error(`Failed to fetch events for city: ${city}`);
      }
      return response.json();
    })
    .then(events => {
      rawEvents = Array.isArray(events) ? events : [];
      allEvents = processEvents(rawEvents);

      // Extract all unique event image URLs
      const eventImageUrls = allEvents
        .map(event => event.extendedProps?.imageUrl)
        .filter(url => url); // Remove null/undefined

      // Prefetch all event images in parallel
      prefetchImages(eventImageUrls);

      filteredEvents = [...allEvents]; // Make a copy for filtering

      buildLegend(CATEGORY_LABELS);
      applyTagFilters();

      setupViewSelectors();
      document.getElementById('loading').style.display = 'none';

      if (!isMobile) {
        highlightToday();
      }
    })
    .catch(error => {
      console.error('Error loading events:', error);
      document.getElementById('loading').innerHTML = '<i class="fas fa-exclamation-circle"></i> Error loading events. Please try again.';
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
            initializeMobileCards(allEvents);
          } else {
            destroyMobileCards();
            const calendarEl = document.getElementById('calendar');
            if (calendarEl) {
              calendarEl.style.display = '';
            }
            initializeCalendar(allEvents);
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
    if (event.url) {
      window.open(event.url, '_blank');
    }
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
  return eventsData.map(event => {
    // Extract group name from URL if exists, otherwise use default
    const urlParts = event.url ? event.url.split('/') : [];
    const groupName = urlParts.length > 3 ? urlParts[3] : 'Unknown Group';

    // Add group to the global set
    eventGroups.add(groupName);

    // Return the event in FullCalendar format
    return {
      id: event.id,
      title: event.name,
      start: event.startDate,
      end: event.endTime,
      description: event.description,
      location: event.location,
      url: event.url,
      extendedProps: {
        group: groupName,
        imageUrl: event.imageUrl,
        tags: Array.isArray(event.tags) ? event.tags : [],
        source: event.source || ''
      },
      backgroundColor: "#0f0f0f0",
      borderColor: "#0f0f0f0",
      textColor: "#000"
    };
  });
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
      // Allow ctrl/cmd click to open in a new tab
      if (info.jsEvent.ctrlKey || info.jsEvent.metaKey) {
        window.open(info.event.url, '_blank');
      } else {
        // Default behavior: navigate in same tab
        window.location.href = info.event.url;
      }

      // Prevent the browser's default link behavior
      info.jsEvent.preventDefault();
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
      // Add tooltips to events
      const tooltip = document.createElement('div');
      tooltip.classList.add('event-tooltip');
      tooltip.innerHTML = `
    ${info.event.title}
    <div>${formatEventDate(info.event.start, info.event.end)}</div>
  `;
      // Check both locations for description
      const description = info.event.extendedProps.description || info.event.description || '';
      const address = info.event.extendedProps.location?.address;
      const parts = [
        info.event.title,
        address,
        description
      ].filter(Boolean).join('\n');

      info.el.setAttribute('title', parts);
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
  const eventsToShow = filterEventsByTags(allEvents).filter(event =>
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
