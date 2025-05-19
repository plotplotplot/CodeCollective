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
      setupFilters(allEvents);
      setupViewSelectors();
      document.getElementById('loading').style.display = 'none';
    })
    .catch(error => {
      console.error('Error loading events:', error);
      document.getElementById('loading').innerHTML = '<i class="fas fa-exclamation-circle"></i> Error loading events. Please try again.';
    });
});

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
      backgroundColor: getGroupColor(groupName),
      borderColor: getGroupColor(groupName),
      textColor: getTextColor(getGroupColor(groupName))
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
          bgDiv.style.position = 'absolute';
          bgDiv.style.top = '0';
          bgDiv.style.left = '0';
          bgDiv.style.right = '0';
          bgDiv.style.bottom = '0';
          bgDiv.style.backgroundImage = `url(${latestEvent.extendedProps.imageUrl})`;
          bgDiv.style.backgroundSize = 'cover';
          bgDiv.style.backgroundPosition = 'center';
          bgDiv.style.opacity = '1';
          bgDiv.style.zIndex = '1'; // Place behind events but above day cell background

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
      titleEl.style.padding = '4px';
      titleEl.style.overflow = 'hidden';
      titleEl.style.textOverflow = 'ellipsis';
      titleEl.style.whiteSpace = 'nowrap';
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
      calendar.changeView(view);

      // Special handling for "All Time" view
      if (view === 'listAll') {
        // Set the date range to show all events (past and future)
        if (allEvents.length > 0) {
          const dates = allEvents.map(event => new Date(event.start));
          const minDate = new Date(Math.min(...dates));
          calendar.gotoDate(minDate);
        }
      }
    });
  });
}

// Set up the filter buttons
function setupFilters(events) {
  const filterContainer = document.getElementById('filter-buttons');

  // Add "All Groups" button
  const allButton = document.createElement('button');
  allButton.innerHTML = '<i class="fas fa-globe"></i> All Groups';
  allButton.className = 'filter-button active';
  allButton.dataset.group = 'all';
  filterContainer.appendChild(allButton);

  // Add a button for each group
  eventGroups.forEach(group => {
    const button = document.createElement('button');
    button.innerHTML = `<i class="fas fa-users"></i> ${formatGroupName(group)}`;
    button.className = 'filter-button';
    button.dataset.group = group;
    button.style.backgroundColor = getLighterColor(getGroupColor(group));
    button.style.color = getTextColor(getLighterColor(getGroupColor(group)));
    filterContainer.appendChild(button);
  });

  // Add click event to filter buttons
  document.querySelectorAll('.filter-button').forEach(button => {
    button.addEventListener('click', function () {
      // Remove active class from all buttons
      document.querySelectorAll('.filter-button').forEach(btn => {
        btn.classList.remove('active');
      });

      // Add active class to clicked button
      this.classList.add('active');

      // Filter events
      const group = this.dataset.group;
      filterEventsByGroup(group);
    });
  });
}

// Filter events by group
function filterEventsByGroup(group) {
  if (group === 'all') {
    filteredEvents = [...allEvents];
  } else {
    filteredEvents = allEvents.filter(event =>
      event.extendedProps.group === group
    );
  }

  calendar.removeAllEventSources();
  calendar.addEventSource(filteredEvents);

  // Force redraw of the calendar to update day cell backgrounds
  const currentDate = calendar.getDate();
  calendar.gotoDate(currentDate);

  // If in "All Time" view, go to earliest date after filtering
  if (currentView === 'listAll' && filteredEvents.length > 0) {
    const dates = filteredEvents.map(event => new Date(event.start));
    const minDate = new Date(Math.min(...dates));
    calendar.gotoDate(minDate);
  }
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

// Show event details popup
function showEventPopup(event) {
  document.getElementById('popup-title').textContent = event.title;

  // Set group info
  const groupEl = document.getElementById('popup-group');
  groupEl.textContent = formatGroupName(event.extendedProps.group);
  groupEl.style.backgroundColor = getLighterColor(getGroupColor(event.extendedProps.group));
  groupEl.style.color = getTextColor(getLighterColor(getGroupColor(event.extendedProps.group)));

  // Set date/time info
  const dateTimeEl = document.getElementById('popup-datetime');
  if (event.start) {
    dateTimeEl.innerHTML = `<i class="far fa-clock"></i> ${formatEventDate(event.start, event.end)}`;
    dateTimeEl.style.display = 'flex';
  } else {
    dateTimeEl.style.display = 'none';
  }

  // Set image if available
  const imageContainer = document.getElementById('popup-image');
  if (event.extendedProps.imageUrl) {
    imageContainer.innerHTML = `<img src="${event.extendedProps.imageUrl}" alt="${event.title}" class="event-image" style="max-width: 100%; border-radius: 8px; margin: 10px 0;">`;
  } else {
    imageContainer.innerHTML = '';
  }

  // Set description with markdown parsing
  document.getElementById('popup-description').innerHTML = event.extendedProps.description || '';

  // Set location information
  const locationEl = document.getElementById('popup-location');
  const location = event.extendedProps.location;
  if (location) {
    let locationHTML = '<i class="fas fa-map-marker-alt" style="color: var(--primary-color); margin-right: 8px;"></i>';
    if (location.name) locationHTML += `<strong>${location.name}</strong><br>`;
    if (location.address) locationHTML += `${location.address}<br>`;
    if (location.city || location.state) {
      locationHTML += `${location.city || ''}, ${location.state || ''} ${location.country || ''}`;
    }
    locationEl.innerHTML = locationHTML;
    locationEl.style.display = 'block';
  } else {
    locationEl.style.display = 'none';
  }

  // Set link
  const linkEl = document.getElementById('popup-link');
  linkEl.href = event.url;

  // Show popup
  window.location.href = event.url;
}


// Get a consistent color based on group name
function getGroupColor(groupName) {
  // Color palette for events
  const colors = [
    '#3a86ff', // Blue
    '#ff006e', // Pink
    '#8338ec', // Purple
    '#fb5607', // Orange
    '#ffbe0b', // Yellow
    '#06d6a0', // Teal
    '#ef476f', // Red
    '#118ab2', // Dark blue
    '#073b4c', // Navy
    '#7209b7'  // Violet
  ];

  // Simple hash function for consistent colors
  const hash = groupName.split('').reduce((acc, char) => {
    return char.charCodeAt(0) + ((acc << 5) - acc);
  }, 0);

  return colors[Math.abs(hash) % colors.length];
}

// Get appropriate text color (black or white) based on background color
function getTextColor(backgroundColor) {
  // For HSL colors
  if (backgroundColor.startsWith('hsl')) {
    const lightness = parseInt(backgroundColor.split(',')[2].replace('%)', ''));
    return lightness > 60 ? '#333333' : '#ffffff';
  }

  // For hex colors - convert to RGB and check luminance
  let color = backgroundColor;
  if (color.startsWith('#')) {
    color = color.substring(1); // Remove #
  }

  // Convert to RGB
  const r = parseInt(color.substr(0, 2), 16);
  const g = parseInt(color.substr(2, 2), 16);
  const b = parseInt(color.substr(4, 2), 16);

  // Calculate luminance
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;

  return luminance > 0.5 ? '#333333' : '#ffffff';
}

// Get a lighter version of the color for buttons
function getLighterColor(color) {
  if (color.startsWith('hsl')) {
    return color.replace('45%', '65%');
  }

  // For hex colors
  if (color.startsWith('#')) {
    // Convert hex to HSL, increase lightness, convert back
    const r = parseInt(color.slice(1, 3), 16) / 255;
    const g = parseInt(color.slice(3, 5), 16) / 255;
    const b = parseInt(color.slice(5, 7), 16) / 255;

    const max = Math.max(r, g, b);
    const min = Math.min(r, g, b);
    let h, s, l = (max + min) / 2;

    if (max === min) {
      h = s = 0; // achromatic
    } else {
      const d = max - min;
      s = l > 0.5 ? d / (2 - max - min) : d / (max + min);

      switch (max) {
        case r: h = (g - b) / d + (g < b ? 6 : 0); break;
        case g: h = (b - r) / d + 2; break;
        case b: h = (r - g) / d + 4; break;
      }

      h /= 6;
    }

    // Increase lightness
    l = Math.min(0.9, l + 0.2);

    // Convert back to hex (simplified)
    return `hsl(${Math.round(h * 360)}, ${Math.round(s * 100)}%, ${Math.round(l * 100)}%)`;
  }

  return color;
}

// Format group name for display
function formatGroupName(name) {
  return name
    .replace(/-/g, ' ')
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

// Close popup when clicking outside the content
window.onclick = function (event) {
  const popup = document.getElementById('event-popup');
  if (event.target === popup) {
    closeEventPopup();
  }
};