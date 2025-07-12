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

  container.innerHTML = ''; // Clear container

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

    let description = event.description || '';
    description = description
      .replace(/<[^>]*>/g, '')           // Remove HTML tags
      .replace(/\*\*(.*?)\*\*/g, '$1')   // Remove markdown bold
      .replace(/\*(.*?)\*/g, '$1')       // Remove markdown italic
      .replace(/\n+/g, ' ')              // Remove newlines
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

// You must define toggleDescription for the 'Show more' button to work
function toggleDescription(eventId) {
  const shortDesc = document.getElementById(`${eventId}-short`);
  const fullDesc = document.getElementById(`${eventId}-full`);
  const btn = document.getElementById(`${eventId}-btn`);
  const expanded = fullDesc.style.display === 'block';

  fullDesc.style.display = expanded ? 'none' : 'block';
  shortDesc.style.display = expanded ? 'block' : 'none';
  btn.textContent = expanded ? 'Show more' : 'Show less';
}

// Fixing this block:
let allEvents = [];

fetch('upcoming_events.json')
  .then(response => response.json())
  .then(events => {
    allEvents = events;
    populateCodeCollectiveEvents(allEvents);
  })
  .catch(error => {
    console.error('Error loading events:', error);
  });
