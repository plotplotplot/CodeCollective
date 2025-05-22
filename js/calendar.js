// Store all events globally
let allEvents = [];
let filteredEvents = [];
let eventGroups = new Set();
let calendar;
let currentView = 'dayGridMonth';

// Fetch and parse event data
document.addEventListener('DOMContentLoaded', function () {
  fetch('upcoming_events.json')
    .then(response => response.json())
    .then(events => {
      allEvents = processEvents(events);
      filteredEvents = [...allEvents]; // Make a copy for filtering
      initializeCalendar(allEvents);
      setupViewSelectors();
      document.getElementById('loading').style.display = 'none';
      
      // Add this: Style today's date after calendar is rendered
      highlightToday();
    })
    .catch(error => {
      console.error('Error loading events:', error);
      document.getElementById('loading').innerHTML = '<i class="fas fa-exclamation-circle"></i> Error loading events. Please try again.';
    });
    
  // Add this: Add CSS for today's date styling
  addTodayStyles();
});

// Add this: Function to add CSS styles for today's date
function addTodayStyles() {
  const style = document.createElement('style');
  style.textContent = `
    .fc .fc-day-today .fc-daygrid-day-number {
      background-color: yellow !important;
      color: black !important;
      border-radius: 50%;
      padding: 5px;
    }
  `;
  document.head.appendChild(style);
}

// Add this: Function to ensure today's date is highlighted correctly
function highlightToday() {
  // This ensures the style is applied even after view changes
  const todayEl = document.querySelector('.fc-day-today .fc-daygrid-day-number');
  if (todayEl) {
    todayEl.style.backgroundColor = 'yellow';
    todayEl.style.color = 'black';
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

// Get the latest event with an image for a specific day
function getLatestEventWithImageForDay(events, date) {
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

// Initialize the FullCalendar
function initializeCalendar(events) {
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
    // Replace the existing code in the dayCellDidMount function
    // Find this part in your code:
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

    // Format event time to display like "3PM"
    formatEventTime: function (date) {
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
        buttonText: 'All Time'
      },
      listYear: {
        type: 'list',
        duration: { year: 1 },
        buttonText: 'Year'
      }
    },
    // Add this: Callback for when view is rendered
    viewDidMount: function() {
      // Apply today highlighting after view changes
      highlightToday();
    }
  });
  calendar.render();
}

// Check if device is mobile
function isMobileDevice() {
  return window.matchMedia('(max-width: 768px)').matches;
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
      
      // Force card view for All Time or mobile
      const effectiveView = (view === 'listAll' || isMobileDevice()) ? 'dayGridMonth' : view;
      calendar.changeView(effectiveView);

      // Special handling for "All Time" view
      if (view === 'listAll') {
        // Show notification about card view being forced
        if (isMobileDevice()) {
          alert('Card view is automatically shown on mobile devices for better readability');
        } else {
          alert('Card view is shown for "All Time" selection to improve performance');
        }
        
        // Set the date range to show all events (past and future)
        if (allEvents.length > 0) {
          const dates = allEvents.map(event => new Date(event.start));
          const minDate = new Date(Math.min(...dates));
          calendar.gotoDate(minDate);
        }
      }
      
      // Reapply today highlighting after view change
      setTimeout(highlightToday, 100);
    });
  });
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