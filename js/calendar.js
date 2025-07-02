// Store all events globally
let allEvents = [];
let filteredEvents = [];
let eventGroups = new Set();
let calendar;
let currentView = 'dayGridMonth';
let isMobile = false;

// Check if device is mobile
function isMobileDevice() {
  //return window.matchMedia('(max-width: 768px)').matches;
  return false;
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


// Fetch and parse event data
document.addEventListener('DOMContentLoaded', function () {

  isMobile = isMobileDevice();

  fetch('upcoming_events.json')
    .then(response => response.json())
    .then(events => {
      allEvents = processEvents(events);

      // Extract all unique event image URLs
      const eventImageUrls = allEvents
        .map(event => event.extendedProps?.imageUrl)
        .filter(url => url); // Remove null/undefined

      // Prefetch all event images in parallel
      prefetchImages(eventImageUrls);

      filteredEvents = [...allEvents]; // Make a copy for filtering

      if (isMobile) {
        initializeMobileCards(allEvents);
      } else {
        initializeCalendar(allEvents);
      }

      populateCodeCollectiveEvents(events);

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

  // Debounce the resize event listener to avoid excessive re-rendering
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
    }, 200); // Adjust debounce time as needed
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
          ${needsMore ? '<button class="more-btn" onclick="toggleDescription(this)"><i class="fas fa-chevron-down"></i> More</button>' : ''}
        </div>
      ` : ''}
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

  // Filter events to show only next 4 weeks starting from today
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const fourWeeksFromNow = new Date(today);
  fourWeeksFromNow.setDate(today.getDate() + 28); // 4 weeks = 28 days
  fourWeeksFromNow.setHours(23, 59, 59, 999); // End of the day

  const filteredEvents = events.filter(event => {
    const eventDate = new Date(event.start);
    return eventDate >= today && eventDate <= fourWeeksFromNow;
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
      const latestEvent = getRandomImageForDay(events, info.date);

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
      titleEl.innerHTML = `${eventTime} ${info.event.title}`;
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
function populateCodeCollectiveEvents(events) {
  const container = document.getElementById('code-collective-events-container');
  if (!container) return;

  // Filter events that have "code-collective" in the URL
  const codeCollectiveEvents = events.filter(event =>
    event.url && event.url.includes('code-collective')
  );

  if (codeCollectiveEvents.length === 0) {
    container.innerHTML = '<p style="text-align: center; color: #999; padding: 20px;">No upcoming Code Collective events at this time.</p>';
    return;
  }

  // Sort events by start date
  codeCollectiveEvents.sort((a, b) => new Date(a.startDate) - new Date(b.startDate));

  // Generate HTML for each event
  const eventsHTML = codeCollectiveEvents.map((event, index) => {
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

    // Convert markdown description to HTML if marked library is available
    let description = event.description || '';
    if (window.marked && description) {
      description = marked.parse(description);
    } else {
      // Simple fallback for basic markdown
      description = description
        .replace(/\*\*(.*?)\*\*/g, '$1')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n/g, '<br>');
    }

    // Create truncated version (first 2-3 lines approximately)
    const words = description.split(' ');
    const truncateLength = 30; // Adjust as needed
    const truncatedDescription = words.length > truncateLength
      ? words.slice(0, truncateLength).join(' ') + '...'
      : description;

    const needsTruncation = words.length > truncateLength;
    const eventId = `event-${index}`;

    const locationText = event.location?.name || 'Location TBD';

    return `
      <div class="cc-event-card">
        <a href="${event.url}" class="cc-event-card-link" target="_blank" rel="noopener noreferrer">

        ${event.imageUrl ? `<img src="${event.imageUrl}" alt="${event.name}" class="event-card-image" loading="lazy">` : ''}
        <div class="cc-event-card-content">
          <h3 class="cc-event-card-title">${event.name}</h3>
          <div class="cc-event-card-date">${formattedDate} at ${formattedTime}</div>
          <div class="cc-event-card-location">${locationText}</div>
          <div class="cc-event-card-description">
            <div id="${eventId}-short" ${needsTruncation ? '' : 'style="display: block;"'}>
              ${truncatedDescription}
            </div>
            ${needsTruncation ? `
              <div id="${eventId}-full" style="display: none;">
                ${description}
              </div>
              <button type="button" class="cc-show-more-btn" onclick="toggleDescription('${eventId}')" id="${eventId}-btn">
                Show more
              </button>
            ` : ''}
          </div>
        </div>
      </a>
      </div>
    `;
  }).join('');

  container.innerHTML = eventsHTML;
}

// Toggle function for show more/less
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