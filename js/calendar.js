// Store all events globally
let allEvents = [];
let filteredEvents = [];
let eventGroups = new Set();
let calendar;
let currentView = 'dayGridMonth';
let isMobile = false;

// Check if device is mobile
function isMobileDevice() {
  return window.matchMedia('(max-width: 768px)').matches;
}

// Fetch and parse event data
document.addEventListener('DOMContentLoaded', function () {
  isMobile = isMobileDevice();

  fetch('upcoming_events.json')
    .then(response => response.json())
    .then(events => {
      allEvents = processEvents(events);
      filteredEvents = [...allEvents]; // Make a copy for filtering

      if (isMobile) {
        initializeMobileCards(allEvents);
      } else {
        initializeCalendar(allEvents);
      }

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

  // Listen for window resize to switch between mobile/desktop views
  window.addEventListener('resize', function () {
    const wasMobile = isMobile;
    isMobile = isMobileDevice();

    if (wasMobile !== isMobile) {
      // View changed, reinitialize
      if (isMobile) {
        destroyCalendar();
        initializeMobileCards(allEvents);
      } else {
        destroyMobileCards();
        initializeCalendar(allEvents);
        addTodayStyles();
      }
    }
  });
});

// Initialize mobile card view
function initializeMobileCards(events) {
  const container = document.getElementById('calendar');
  container.innerHTML = '';
  container.className = 'mobile-cards-container';

  // Filter events to only show future events (after today)
  const today = new Date();
  today.setHours(0, 0, 0, 0); // Set to start of today

  const futureEvents = events.filter(event => {
    const eventDate = new Date(event.start);
    return eventDate >= today;
  });

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
function toggleDescription(button) {
  const card = button.closest('.event-card');
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
        event.location.address,
        event.location.city,
        event.location.state
      ].filter(Boolean).join(', ')}
    </span>
  </div>
` : ''}


      </div>
      ${description ? `
        <div class="card-description">
          <div class="card-description-short">${shortDesc}</div>
          <div class="card-description-full markdown-content" style="display: none;"></div>
          ${needsMore ? '<button class="more-btn" onclick="toggleDescription(this)"><i class="fas fa-chevron-down"></i> More</button>' : ''}
        </div>
      ` : ''}
      <div class="card-footer">
        ${event.extendedProps?.group ? `<div class="card-group">${event.extendedProps.group}</div>` : ''}
        ${event.url ? '<div class="card-link-indicator"><i class="fas fa-external-link-alt"></i></div>' : ''}
      </div>
  `;

  // Process markdown for full description if needed
  if (description && needsMore) {
    const fullDescContainer = card.querySelector('.card-description-full');
    if (fullDescContainer) {
      fullDescContainer.innerHTML = marked.parse(description);
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
  container.innerHTML = '';
  container.className = '';
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

// All styles are now handled externally in CSS file

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
        imageUrl: event.imageUrl
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

  // Format the date to YYYY-MM-DD for comparison
  const dateStr = date.toISOString().split('T')[0];

  // Filter events that are on this day and have an image
  const dayEvents = events.filter(event => {
    const eventDate = new Date(event.start).toISOString().split('T')[0];
    return eventDate === dateStr && event.extendedProps.imageUrl;
  });

  // If no events with images for this day, return null
  if (dayEvents.length === 0) return null;

  // Sort events by start time, descending (latest first)
  dayEvents.sort((a, b) => new Date(b.start) - new Date(a.start));

  // Return the latest event
  return dayEvents[0];
}

// Initialize the FullCalendar (desktop only)
function initializeCalendar(events) {
  if (isMobile) return;

  const calendarEl = document.getElementById('calendar');
  calendar = new FullCalendar.Calendar(calendarEl, {
    initialView: 'dayGridMonth',
    headerToolbar: {
      left: 'prev,next today',
      center: 'title',
      right: ''  // We're using our custom view selectors instead
    },
    events: events,
    eventClick: function (info) {
      window.location.href = info.url;
    },
    eventTimeFormat: {
      hour: 'numeric',
      minute: '2-digit',
      meridiem: 'short'
    },
    height: 'auto',
    dayMaxEvents: true, // Allow "more" link when too many events
    dayCellDidMount: function (info) {
      // Get the latest event with an image for this day
      const latestEvent = getLatestEventWithImageForDay(filteredEvents, info.date);

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
      titleEl.innerHTML = `<strong>${eventTime} ${info.event.title}</strong>`;
      eventEl.appendChild(titleEl);

      return { domNodes: [eventEl] };
    },
    eventDidMount: function (info) {
      // Add tooltips to events
      const tooltip = document.createElement('div');
      tooltip.classList.add('event-tooltip');
      tooltip.innerHTML = `
        <strong>${info.event.title}</strong>
        <div>${formatEventDate(info.event.start, info.event.end)}</div>
      `;

      info.el.setAttribute('title', info.event.title);
    },
    views: {
      listAll: {
        type: 'list',
        duration: { years: 10 },
        buttonText: 'Card View',
      },
      listYear: {
        type: 'list',
        duration: { year: 1 },
        buttonText: 'Year'
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
  let eventsToShow = [...allEvents];
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  // Always filter to future events first
  eventsToShow = allEvents.filter(event => {
    const eventDate = new Date(event.start);
    return eventDate >= today;
  });

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