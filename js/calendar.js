/* calendar.js
   - Adds FullCalendar list view toggle (month list) and remembers preference via localStorage.
   - Avoids duplicate function names for "toggleDescription" by renaming card version.
*/

// ========================
// Globals / State
// ========================
let allEvents = [];
let filteredEvents = [];
let eventGroups = new Set();
let calendar;

// Restore saved view; fallback to your 4-week grid
const savedView = localStorage.getItem('calendarView');
let currentView =
  (savedView === 'listMonth' || savedView === 'dayGridFourWeek') ? savedView : 'dayGridFourWeek';

let isMobile = false;

// ========================
// Helpers
// ========================
function isMobileDevice() {
  return window.matchMedia('(max-width: 768px)').matches;
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

// Format event time to display like "3PM"
function formatEventTime(date) {
  if (!date) return '';

  const hours = date.getHours();
  const minutes = date.getMinutes();

  const period = hours >= 12 ? 'PM' : 'AM';
  const displayHours = hours % 12 || 12;

  return minutes === 0
    ? `${displayHours}${period}`
    : `${displayHours}:${minutes.toString().padStart(2, '0')}${period}`;
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

// Strip markdown (for short snippets)
function stripMarkdown(text) {
  return text
    .replace(/^#+\s+/gm, '')                 // headings
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // links -> text
    .replace(/\*\*([^*]+)\*\*/g, '$1')       // bold
    .replace(/\*([^*]+)\*/g, '$1')           // italics
    .replace(/`([^`]+)`/g, '$1')             // code
    .replace(/^\s*[-*+]\s+/gm, '')           // list markers
    .replace(/\n+/g, ' ');                   // newlines to spaces
}

// ========================
// Event processing
// ========================
function processEvents(eventsData) {
  return eventsData.map(event => {
    // Extract group name from URL if exists, otherwise use default
    const urlParts = event.url ? event.url.split('/') : [];
    const groupName = urlParts.length > 3 ? urlParts[3] : 'Unknown Group';

    // Track groups
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
        imageUrl: event.imageUrl
      },
      backgroundColor: "#0f0f0f0",
      borderColor: "#0f0f0f0",
      textColor: "#000"
    };
  });
}

// ========================
// DOM Ready / Fetch
// ========================
document.addEventListener('DOMContentLoaded', function () {
  isMobile = isMobileDevice();

  fetch('upcoming_events.json')
    .then(response => response.json())
    .then(events => {
      allEvents = processEvents(events);

      // Prefetch event images
      const eventImageUrls = allEvents
        .map(event => event.extendedProps?.imageUrl)
        .filter(Boolean);
      prefetchImages(eventImageUrls);

      filteredEvents = [...allEvents];

      if (isMobile) {
        initializeMobileCards(allEvents);
      } else {
        initializeCalendar(allEvents);
      }

      populateCodeCollectiveEvents(events);

      setupViewSelectors();
      const loadingEl = document.getElementById('loading');
      if (loadingEl) loadingEl.style.display = 'none';

      if (!isMobile) {
        highlightToday();
      }
    })
    .catch(error => {
      console.error('Error loading events:', error);
      const loadingEl = document.getElementById('loading');
      if (loadingEl) {
        loadingEl.innerHTML = '<i class="fas fa-exclamation-circle"></i> Error loading events. Please try again.';
      }
    });

  // Add CSS for today's date styling (desktop only)
  if (!isMobile) {
    addTodayStyles();
  }

  // Debounced resize handling to swap mobile/cards vs calendar
  let resizeTimeout;
  window.addEventListener('resize', function () {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
      const wasMobile = isMobile;
      isMobile = isMobileDevice();

      if (wasMobile !== isMobile) {
        if (isMobile) {
          destroyCalendar();
          initializeMobileCards(allEvents);
        } else {
          destroyMobileCards();
          initializeCalendar(allEvents);
          addTodayStyles();
        }
      }
    }, 200);
  });
});

// ========================
// Mobile Cards View
// ========================
function initializeMobileCards(events) {
  const container = document.getElementById('calendar');
  container.innerHTML = '';
  container.className = 'mobile-cards-container';

  // Only future events
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const futureEvents = events
    .filter(event => new Date(event.start) >= today)
    .sort((a, b) => new Date(a.start) - new Date(b.start));

  futureEvents.forEach(event => {
    const eventCard = createEventCard(event);
    container.appendChild(eventCard);
  });

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

// Renamed to avoid clashing with the CC events "toggleDescription"
function toggleCardDescription(button) {
  const card = button.closest('.card-content');
  const shortDesc = card.querySelector('.card-description-short');
  const fullDesc = card.querySelector('.card-description-full');
  const moreBtn = card.querySelector('.more-btn');

  if (fullDesc.style.display === 'none' || !fullDesc.style.display) {
    shortDesc.style.display = 'none';
    fullDesc.style.display = 'block';
    moreBtn.innerHTML = '<i class="fas fa-chevron-up"></i> Less';
  } else {
    shortDesc.style.display = 'block';
    fullDesc.style.display = 'none';
    moreBtn.innerHTML = '<i class="fas fa-chevron-down"></i> More';
  }
}

function createEventCard(event) {
  const card = document.createElement('div');
  card.className = 'card-content';

  const startTime = formatEventTime(new Date(event.start));
  const endTime = event.end ? formatEventTime(new Date(event.end)) : '';
  const timeRange = endTime ? `${startTime} - ${endTime}` : startTime;

  // Full date
  const eventDate = new Date(event.start);
  const fullDate = eventDate.toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });

  // Description with markdown support
  const rawDescription = event.description || '';
  const description = rawDescription.trim();
  const maxDescLength = 100;
  const needsMore = description.length > maxDescLength;

  const shortDesc = needsMore
    ? stripMarkdown(description).substring(0, maxDescLength) + '...'
    : stripMarkdown(description);

  card.innerHTML = `
    ${event.extendedProps.imageUrl
      ? `<div class="card-image" style="background-image: url(${event.extendedProps.imageUrl})"></div>`
      : '<div class="card-image-placeholder"><i class="fas fa-calendar-alt"></i></div>'
    }
    <h3 class="card-title">${event.title}</h3>
    <div class="card-meta">
      <div class="card-time">
        ${fullDate}, ${timeRange}
      </div>
      ${event.location ? `
        <div class="card-location">
          <i class="fas fa-map-marker-alt"></i>
          <span class="location-address">
            ${[ event.location.address ].filter(Boolean).join(', ')}
          </span>
        </div>` : ''}
    </div>
    ${description ? `
      <div class="card-description">
        <div class="card-description-short">${shortDesc}</div>
        <div class="card-description-full markdown-content" style="display: none;"></div>
        ${needsMore ? '<button class="more-btn" onclick="toggleCardDescription(this)"><i class="fas fa-chevron-down"></i> More</button>' : ''}
      </div>` : ''}
  `;

  // Render markdown for full description if needed
  if (description && needsMore) {
    const fullDescContainer = card.querySelector('.card-description-full');
    if (fullDescContainer && window.marked) {
      fullDescContainer.innerHTML = marked.parse(description);
    }
  }

  // Card click (ignore "more" button and links)
  card.addEventListener('click', function (e) {
    if (e.target.closest('.more-btn') || e.target.closest('a')) return;
    if (event.url) window.open(event.url, '_blank');
  });

  return card;
}

function destroyMobileCards() {
  const container = document.getElementById('calendar');
  container.innerHTML = '';
  container.className = '';
}

// ========================
// FullCalendar View (Desktop)
// ========================
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

// Highlight today's number badge (grid only)
function highlightToday() {
  if (isMobile) return;
  const todayEl = document.querySelector('.fc-day-today .fc-daygrid-day-number');
  if (todayEl) {
    todayEl.style.backgroundColor = 'yellow';
    todayEl.style.color = 'black';
    todayEl.style.fontWeight = 'bold';
  }
}

// Get a random event with an image for a specific day (desktop only)
function getRandomImageForDay(events, date) {
  if (isMobile) return null;

  const dateStr = date.getFullYear() + '-' +
    String(date.getMonth() + 1).padStart(2, '0') + '-' +
    String(date.getDate()).padStart(2, '0');

  const dayEvents = events.filter(event => {
    const eventDate = new Date(event.start);
    const eventDateStr = eventDate.getFullYear() + '-' +
      String(eventDate.getMonth() + 1).padStart(2, '0') + '-' +
      String(eventDate.getDate()).padStart(2, '0');
    return eventDateStr === dateStr && event.extendedProps.imageUrl;
  });

  if (dayEvents.length === 0) return null;

  const randomIndex = Math.floor(Math.random() * dayEvents.length);
  return dayEvents[randomIndex];
}

function initializeCalendar(events) {
  if (isMobile) return;

  // Prepare "today" as a Date object (and keep a copy for validRange)
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const validRangeStart = new Date(today);

  const calendarEl = document.getElementById('calendar');
  calendar = new FullCalendar.Calendar(calendarEl, {
    // Honor saved view: 'dayGridFourWeek' or 'listMonth'
    initialView: currentView,

    // Declare custom 4-week grid and list-month
    views: {
      dayGridFourWeek: {
        type: 'dayGrid',
        duration: { weeks: 4 },
        buttonText: 'Calendar',
        fixedWeekCount: true,
        height: 'auto',
      },
      listMonth: { buttonText: 'List' }
    },

    headerToolbar: {
      left: 'prev,next today',
      center: 'title',
      right: 'dayGridFourWeek,listMonth'
    },

    validRange: { start: validRangeStart },

    events: events,

    eventClick: function (info) {
      if (info.jsEvent.ctrlKey || info.jsEvent.metaKey) {
        window.open(info.event.url, '_blank');
      } else {
        window.location.href = info.event.url;
      }
      info.jsEvent.preventDefault();
    },

    eventTimeFormat: {
      hour: 'numeric',
      minute: '2-digit',
      meridiem: 'short'
    },

    height: 'auto',
    dayMaxEvents: true,

    dayCellDidMount: function (info) {
      // Grid-only enhancement: background image for future days
      const cellDate = new Date(info.date);
      cellDate.setHours(0, 0, 0, 0);
      if (cellDate < validRangeStart) return;

      const eventWithImage = getRandomImageForDay(events, info.date);
      if (eventWithImage && eventWithImage.extendedProps.imageUrl) {
        const cellEl = info.el;
        const dayFrame = cellEl.querySelector('.fc-daygrid-day-frame');
        if (dayFrame) {
          dayFrame.classList.add('has-event-background');

          const bgDiv = document.createElement('div');
          bgDiv.classList.add('fc-day-background');
          bgDiv.style.backgroundImage = `url(${eventWithImage.extendedProps.imageUrl})`;

          dayFrame.style.position = 'relative';
          dayFrame.prepend(bgDiv);

          const eventContent = dayFrame.querySelector('.fc-daygrid-day-events');
          if (eventContent) {
            eventContent.style.position = 'relative';
            eventContent.style.zIndex = '2';
          }
        }
      }
    },

    eventContent: function (info) {
      // Use default rendering for list views
      if (info.view.type.includes('list')) return;

      const eventEl = document.createElement('div');
      eventEl.classList.add('fc-event-content-wrapper');

      const eventTime = formatEventTime(info.event.start);
      const titleEl = document.createElement('div');
      titleEl.classList.add('fc-event-title');
      titleEl.innerHTML = `${eventTime} ${info.event.title}`;
      eventEl.appendChild(titleEl);

      return { domNodes: [eventEl] };
    },

    eventDidMount: function (info) {
      // Tooltip content; prefer top-level location, fallback to extendedProps if ever present
      const description = info.event.extendedProps.description || info.event.description || '';
      const address = (info.event.location && info.event.location.address)
        || (info.event.extendedProps && info.event.extendedProps.location && info.event.extendedProps.location.address);

      const parts = [ info.event.title, address, description ].filter(Boolean).join('\n');
      info.el.setAttribute('title', parts);
    },

    viewDidMount: function () {
      // Highlight today for grid views
      if (calendar.view.type.includes('dayGrid')) highlightToday();
    },

    // Persist the selected view
    datesSet: function (arg) {
      currentView = arg.view.type; // 'dayGridFourWeek' or 'listMonth'
      localStorage.setItem('calendarView', currentView);
    }
  });

  calendar.render();
}

// ========================
// Custom View Selectors (optional external buttons)
// ========================
function setupViewSelectors() {
  const buttons = document.querySelectorAll('.view-selector');
  if (!buttons.length) return;

  buttons.forEach(button => {
    button.addEventListener('click', function () {
      buttons.forEach(btn => btn.classList.remove('active'));
      this.classList.add('active');

      const view = this.dataset.view; // Expect 'dayGridFourWeek' or 'listMonth'
      currentView = view;
      localStorage.setItem('calendarView', currentView);

      if (isMobile) {
        // Mobile stays on cards; we just re-render cards (keeps UX consistent if you later add filters)
        handleMobileViewChange(view);
      } else if (calendar) {
        // If you had any custom alias like 'listAll', map it here as needed
        const effectiveView = (view === 'listAll') ? 'dayGridFourWeek' : view;
        calendar.changeView(effectiveView);
        setTimeout(highlightToday, 100);
      }
    });
  });

  // Reflect saved/initial view
  const activeBtn = document.querySelector(`.view-selector[data-view="${currentView}"]`);
  if (activeBtn) activeBtn.classList.add('active');
}

function handleMobileViewChange(view) {
  // Currently always cards; future filters can go here
  let eventsToShow = [...allEvents];

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  eventsToShow = allEvents.filter(event => new Date(event.start) >= today);

  initializeMobileCards(eventsToShow);
}

// ========================
// Code Collective Events (sidebar/grid below)
// ========================
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

    const eventCard = document.createElement('div');
    eventCard.className = 'cc-event-card';

    const eventLink = document.createElement('a');
    eventLink.href = event.url;
    eventLink.className = 'cc-event-card-link';
    eventLink.target = '_blank';
    eventLink.rel = 'noopener noreferrer';

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
    title.textContent = event.name;

    const dateDiv = document.createElement('div');
    dateDiv.className = 'cc-event-card-date';
    dateDiv.textContent = `${formattedDate} at ${formattedTime}`;

    const locationDiv = document.createElement('div');
    locationDiv.className = 'cc-event-card-location';
    locationDiv.textContent = event.location?.name || 'Location TBD';

    const descriptionDiv = document.createElement('div');
    descriptionDiv.className = 'cc-event-card-description';

    // Safe plain text description
    let description = (event.description || '')
      .replace(/<[^>]*>/g, '') // strip HTML
      .replace(/\*\*(.*?)\*\*/g, '$1')
      .replace(/\*(.*?)\*/g, '$1')
      .replace(/\n+/g, ' ')
      .trim();

    const truncatedDescription = description.length > 200
      ? description.substring(0, 200) + '...'
      : description;

    const needsTruncation = description.length > 200;
    const eventId = `event-${index}`;

    const shortDesc = document.createElement('div');
    shortDesc.id = `${eventId}-short`;
    shortDesc.textContent = truncatedDescription;
    if (!needsTruncation) shortDesc.style.display = 'block';

    descriptionDiv.appendChild(shortDesc);

    if (needsTruncation) {
      const fullDesc = document.createElement('div');
      fullDesc.id = `${eventId}-full`;
      fullDesc.style.display = 'none';
      fullDesc.textContent = description;

      const showMoreBtn = document.createElement('button');
      showMoreBtn.type = 'button';
      showMoreBtn.className = 'cc-show-more-btn';
      showMoreBtn.id = `${eventId}-btn`;
      showMoreBtn.textContent = 'Show more';
      showMoreBtn.onclick = () => toggleDescription(eventId);

      descriptionDiv.appendChild(fullDesc);
      descriptionDiv.appendChild(showMoreBtn);
    }

    contentDiv.appendChild(title);
    contentDiv.appendChild(dateDiv);
    contentDiv.appendChild(locationDiv);
    contentDiv.appendChild(descriptionDiv);
    eventLink.appendChild(contentDiv);
    eventCard.appendChild(eventLink);
    container.appendChild(eventCard);
  });
}

// Toggle for Code Collective cards (kept original name here)
function toggleDescription(eventId) {
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

// ========================
// Popup close handler (if used elsewhere)
// ========================
window.onclick = function (event) {
  const popup = document.getElementById('event-popup');
  if (event.target === popup && typeof closeEventPopup === 'function') {
    closeEventPopup();
  }
};
