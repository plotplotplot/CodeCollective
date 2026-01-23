class OurHeader extends HTMLElement {
    connectedCallback() {
        this.innerHTML = `
            <nav class="main-nav" aria-label="Main Navigation">
                <div class="navbar dark-mode">
                <a href="/#main">Home</a>
                <a href="/balticonomy/">Balticonomy</a>
                <a href="/#get-involved">Join Us</a>
                <a href="/newsletter/">Newsletter</a>
                </div>
            </nav>
        `
    }
}

class OurFooter extends HTMLElement {
    connectedCallback() {
        this.innerHTML = `
            <footer id="footer">
                <ul class="copyright">
                    <li>&copy; Code Collective 2025</li>
                </ul>
            </footer>
        `
    }
}

class OurSocials extends HTMLElement {
    connectedCallback() {
        this.innerHTML = `
            <aside id="socialButtons" class="social__container">
                <a
                    href="https://matrix.to/#/#code-collective:matrix.org"
                    target="_blank"
                    class="social__link"
                >
                    <button class="social__button">
                        <img
                            src="/images/element_logo.svg"
                            alt="Matrix icon"
                            class="social__icon"
                        />
                    </button>
                </a>
                <a
                    href="https://chat.whatsapp.com/JFlI9aRvNaGCTU2lOFXpOt"
                    target="_blank"
                    class="social__link"
                >
                    <button class="social__button">
                        <img
                            src="/images/WhatsApp.svg.webp"
                            alt="WhatsApp icon"
                            class="social__icon"
                        />
                    </button>
                </a>
                <a
                    href="https://github.com/juliancoy/codecollective"
                    target="_blank"
                    class="social__link"
                >
                    <button class="social__button">
                        <img
                            src="/images/github_icon.png"
                            alt="GitHub icon"
                            class="social__icon"
                        />
                    </button>
                </a>
                <a
                    href="https://t.me/codecollective"
                    target="_blank"
                    class="social__link"
                >
                    <button class="social__button">
                        <img
                            src="/images/Telegram_logo.svg"
                            alt="Telegram icon"
                            class="social__icon"
                        />
                    </button>
                </a>
                <a
                    href="https://www.facebook.com/groups/687416533909466/"
                    target="_blank"
                    class="social__link"
                >
                    <button class="social__button">
                        <img
                            src="/images/Facebook_f_logo.svg"
                            alt="Facebook icon"
                            class="social__icon"
                        />
                    </button>
                </a>
                <a
                    href="https://discord.gg/ZSRhJmJmnN"
                    target="_blank"
                    class="social__link"
                >
                    <button class="social__button">
                        <img
                            src="/images/discord.jpg"
                            alt="Discord icon"
                            class="social__icon"
                        />
                    </button>
                </a>
            </aside>
        `;
    }
}

class CalendarLegend extends HTMLElement {
    connectedCallback() {
        this.innerHTML = `
            <aside class="calendar-legend" aria-label="Event category filters">
                <div class="legend-title">Filter by category:</div>
                <div class="legend-items" id="calendar-legend-items"></div>
            </aside>
            <button type="button" id="legend-visibility-toggle" class="legend-toggle-button" aria-expanded="true">
                Show legend
            </button>
        `;
    }
}

customElements.define('our-header', OurHeader)
customElements.define('our-footer', OurFooter)
customElements.define('our-slack-link', OurSocials)
customElements.define('calendar-legend', CalendarLegend)
