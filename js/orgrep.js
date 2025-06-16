
fetch('./orgs_iframe.json')
  .then(response => response.json())
  .then(data => {
    const sidebar = document.getElementById('sidebar');
    const content = document.getElementById('organizations');

    // Function to update URL without reloading
    function updateUrl(type) {
      const url = new URL(window.location);
      url.hash = `#type=${encodeURIComponent(type)}`;
      window.history.pushState({}, '', url);
    }

    // Function to read URL and show appropriate content
    function checkUrlAndLoadContent() {
      const hash = window.location.hash;
      const typeMatch = hash.match(/#type=(.+)/);

      if (typeMatch) {
        const type = decodeURIComponent(typeMatch[1]);
        if (data[type]) {
          displayOrgsByType(type, data[type]);
          return;
        }
      }

      // Default view if no valid type in URL
      content.innerHTML = "<p>Select a category from the sidebar to view organizations</p>";
    }

    // Initialize with URL check
    checkUrlAndLoadContent();

    // Handle browser back/forward buttons
    window.addEventListener('popstate', checkUrlAndLoadContent);

    for (const type of Object.keys(data)) {
      // Create heading for sidebar
      const heading = document.createElement('h2');
      heading.textContent = type;
      heading.style.cursor = 'pointer';
      heading.onclick = () => {
        updateUrl(type);
        displayOrgsByType(type, data[type]);
        populateOrgLinks(type);
      };
      sidebar.appendChild(heading);
    }

    // Function to populate org links for a selected type
    function populateOrgLinks(type) {
      // Remove existing org links
      const existingLinks = sidebar.querySelectorAll('a');
      existingLinks.forEach(link => link.remove());

      const orgs = data[type];
      orgs.forEach(org => {
        const link = document.createElement('a');
        link.href = `#org=${encodeURIComponent(org["Group Name"])}`;
        link.textContent = org["Group Name"];
        link.onclick = (e) => {
          e.preventDefault();
          displaySingleOrg(org);
        };
        sidebar.appendChild(link);
      });
    }


    function displayOrgsByType(type, orgs) {
      content.innerHTML = "";
      const typeHeading = document.createElement('h2');
      typeHeading.textContent = type;
      typeHeading.style.color = 'white';
      typeHeading.style.marginBottom = '1em';
      typeHeading.style.width = '100%';
      content.appendChild(typeHeading);

      const cardsContainer = document.createElement('div');
      cardsContainer.style.display = 'flex';
      cardsContainer.style.flexWrap = 'wrap';
      cardsContainer.style.gap = '2em';
      cardsContainer.style.justifyContent = 'center';

      orgs.forEach(org => {
        const card = createOrgCard(org);
        cardsContainer.appendChild(card);
      });

      content.appendChild(cardsContainer);
    }

    function displaySingleOrg(org) {
      content.innerHTML = "";
      const card = createOrgCard(org);
      content.appendChild(card);
    }

    function createOrgCard(org) {
      const title = org["Group Name"];
      let url = org["Website"];
      let screenshotPath = org["screenshot"];
      const description = org["Description"] || "No description available.";

      // Only prepend https:// if the URL doesn't start with http://, https://, or ./
      const ensureHttps = (u) => {
        if (!u) return null;
        return (/^(https?:\/\/|\.\/)/i.test(u)) ? u : 'https://' + u;
      };
      url = ensureHttps(url);
      screenshotPath = ensureHttps(screenshotPath);

      const card = document.createElement('div');
      card.className = 'iframe-card';

      const headerLink = document.createElement('a');
      headerLink.href = url;
      headerLink.target = '_blank';
      headerLink.className = 'card-header';
      headerLink.textContent = title;

      const desc = document.createElement('div');
      desc.className = 'description-box';
      desc.innerHTML = `<p>${description}</p>`;

      card.appendChild(headerLink);
      card.appendChild(desc);

      if (screenshotPath) {
        const img = document.createElement('img');
        img.src = screenshotPath;
        img.alt = title;
        img.title = title;
        card.appendChild(img);
      } else {
        const iframe = document.createElement('iframe');
        iframe.src = url;
        iframe.title = title;
        iframe.loading = "lazy";
        card.appendChild(iframe);
      }

      return card;
    }
  })
  .catch(error => {
    console.error("Error loading organizations:", error);
  });