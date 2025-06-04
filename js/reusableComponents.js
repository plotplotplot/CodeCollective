class OurHeader extends HTMLElement {
    connectedCallback() {
        this.innerHTML = `
            <nav class="main-nav">
                <div class="navbar dark-mode">
                    <a href="/index.html">Home</a>
                    <a href="/calendar.html">Calendar</a>
                    <a href="/curriculum.html">Curriculum</a>
                    <a href="/getinvolved.html">Get Involved!</a>
                    <a href="/sponsors.html">Sponsors</a>
                    <a href="/about-us.html">About Us</a>
                </div>
                <button class="mobile-nav-bars">
                    <div class="top bar"></div>
                    <div class="middle bar"></div>
                    <div class="bottom bar"></div>
                </button>
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
                    href="https://www.meetup.com/code-collective/"
                    target="_blank"
                    class="social__link"
                >
                    <button class="social__button">
                        <img
                            src="/images/meetup_icon.png"
                            alt="Meetup icon"
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
            </aside>
        `;
    }
}

customElements.define('our-header', OurHeader)
customElements.define('our-footer', OurFooter)
customElements.define('our-slack-link', OurSocials)