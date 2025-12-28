#!/usr/bin/env python3
"""Generate `inde.html` as an index of the newsletter HTML files."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable, Sequence
import re


NEWSLETTER_DIR = Path("newsletter")
OUTPUT_FILE = NEWSLETTER_DIR / "index.html"
SNIPPET_WORD_LIMIT = 40
IGNORED_TAGS = {"script", "style", "noscript", "nav", "video"}
IGNORED_CLASS_KEYWORDS = ("carousel", "speed-zone")
DATE_PATTERN = re.compile(r"^(\d{4})(\d{2})(\d{2})")


class _NewsletterParser(HTMLParser):
    """Extract the <title> and early body text while skipping scripts/styles."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_open = False
        self.body_open = False
        self.body_seen = False
        self._skip_stack: list[str] = []
        self._title_parts: list[str] = []
        self._body_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: Sequence[tuple[str, str]]) -> None:
        lower = tag.lower()
        if lower == "title":
            self.title_open = True
        elif lower == "body":
            self.body_open = True
            self.body_seen = True
        if self._should_skip_tag(lower, attrs):
            self._skip_stack.append(lower)

    def handle_endtag(self, tag: str) -> None:
        lower = tag.lower()
        if lower == "title":
            self.title_open = False
        elif lower == "body":
            self.body_open = False
        if self._skip_stack and self._skip_stack[-1] == lower:
            self._skip_stack.pop()

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text:
            return
        if self.title_open:
            self._title_parts.append(text)
        elif not self._skip_stack and (self.body_open or not self.body_seen):
            self._body_parts.append(text)

    def _should_skip_tag(
        self, tag: str, attrs: Sequence[tuple[str, str]]
    ) -> bool:
        if tag in IGNORED_TAGS:
            return True
        class_attr = next(
            (value for key, value in attrs if key.lower() == "class"), ""
        ).lower()
        if any(keyword in class_attr for keyword in IGNORED_CLASS_KEYWORDS):
            return True
        return False

    @property
    def title(self) -> str:
        return " ".join(self._title_parts).strip()

    @property
    def snippet(self) -> str:
        return " ".join(self._body_parts).strip()


@dataclass
class NewsletterSummary:
    path: Path
    title: str
    snippet: str
    published: date | None
    relative_path: Path

    @property
    def href(self) -> str:
        return self.relative_path.as_posix()

    @property
    def published_display(self) -> str | None:
        if not self.published:
            return None
        return f"{self.published:%B} {self.published.day}, {self.published:%Y}"


def _word_snippet(text: str, limit: int) -> str:
    words = text.split()
    if not words:
        return "No preview available."
    snippet = " ".join(words[:limit])
    if len(words) > limit:
        snippet = snippet.rstrip() + "…"
    return snippet


def _strip_nav_text(text: str) -> str:
    """Remove repeated navigation labels if they leaked into the snippet."""
    marker = "☀️"
    if marker not in text:
        return text
    prefix = text.split(marker, 1)[0]
    if "Home" in prefix and "Balticonomy" in prefix:
        return text.split(marker, 1)[1].lstrip()
    return text


def _trim_nav_prefix(text: str) -> str:
    nav_words = {"home", "balticonomy", "calendar", "about", "us", "join", "newsletter", "☀️"}
    words = text.split()
    while words and words[0].strip(".,;:—–-\"'").lower() in nav_words:
        words.pop(0)
    return " ".join(words)


def _date_from_filename(stem: str) -> date | None:
    match = DATE_PATTERN.match(stem)
    if not match:
        return None
    year, month, day = map(int, match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def summarize_html(file_path: Path) -> NewsletterSummary:
    parser = _NewsletterParser()
    parser.feed(file_path.read_text(encoding="utf-8", errors="ignore"))
    parser.close()
    title = parser.title or file_path.stem
    cleaned = _strip_nav_text(parser.snippet or "")
    snippet = _word_snippet(_trim_nav_prefix(cleaned), SNIPPET_WORD_LIMIT)
    published = _date_from_filename(file_path.stem)
    rel_path = file_path.relative_to(NEWSLETTER_DIR)
    return NewsletterSummary(
        path=file_path,
        title=title,
        snippet=snippet,
        published=published,
        relative_path=rel_path,
    )


def gather_newsletter_entries(directory: Path) -> list[NewsletterSummary]:
    if not directory.is_dir():
        raise FileNotFoundError(f"{directory} is not a directory")
    html_files = sorted(
        (path for path in directory.glob("*.html") if path.name != OUTPUT_FILE.name),
        reverse=True,
    )
    return [summarize_html(path) for path in html_files]


def render_html(entries: Iterable[NewsletterSummary]) -> str:
    entry_blocks = []
    for entry in entries:
        date_line = (
            f"                <p class=\"event-date\">{escape(entry.published_display)}</p>\n"
            if entry.published_display
            else ""
        )
        entry_blocks.append(
            f"""            <article class="event-card">
              <div class="event-content">
{date_line}                <h2 class="event-title"><a href="{escape(entry.href)}">{escape(entry.title)}</a></h2>
                <p class="event-description">{escape(entry.snippet)}</p>
              </div>
            </article>"""
        )
    entries_html = (
        "\n".join(entry_blocks)
        if entry_blocks
        else '            <p class="event-description">No newsletter HTML files found.</p>'
    )
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no" />
    <title>Code Collective | Newsletter Index</title>
    <meta name="description" content="Newsletter archive previews from Code Collective." />
    <link rel="icon" href="/images/favicons/favicon.png" />
    <link rel="stylesheet" href="/css/master.css" />
    <link rel="stylesheet" href="/css/carousel.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
      #newsletter-events-container {{
        display: flex;
        flex-direction: column;
        gap: 1rem;
      }}
      .event-card {{
        display: flex;
        background: rgba(0, 0, 0, 0.65);
        padding: 1rem;
        border-radius: 1rem;
      }}
      .event-date {{
        font-size: 0.85rem;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        margin: 0 0 0.25rem;
        color: #fff200;
      }}
    </style>
  </head>
  <body id="body">
    <video id="bg-video" autoplay loop muted playsinline>
      <source src="/videos/baltimorenight_15s_crossfaded.mp4" type="video/mp4">
      Your browser does not support the video tag.
    </video>

    <nav class="main-nav" aria-label="Main Navigation">
      <div class="navbar dark-mode">
        <a href="/#main">Home</a>
        <a href="/balticonomy/">Balticonomy</a>
        <a href="/calendar.html?city=baltimore">Calendar</a>
        <a href="/newsletter/">Newsletter</a>
      </div>
    </nav>

    <main id="wrapper" class="longform dark-mode" style="padding: 0; margin: 0;">
      <section id="main" class="longform dark-mode" style="padding: 0; margin: 0;">
        <section class="about-us" id="newsletter-index" aria-label="Newsletter index overview">
          <header>
            <h1 class="event-title">Newsletter</h1>
          </header>
          <section class="code-collective-events" aria-label="Newsletter previews">
            <div id="newsletter-events-container">
{entries_html}
            </div>
          </section>
        </section>
        <script src="/js/populateEvents.js"></script>
        <script src="/js/carousel.js"></script>
      </section>
      <our-footer></our-footer>
      <our-slack-link></our-slack-link>
    </main>

    <script type="module" src="/js/reusableComponents.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/fullcalendar/6.1.8/index.global.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  </body>
</html>
"""


def main() -> None:
    entries = gather_newsletter_entries(NEWSLETTER_DIR)
    OUTPUT_FILE.write_text(render_html(entries), encoding="utf-8")


if __name__ == "__main__":
    main()
