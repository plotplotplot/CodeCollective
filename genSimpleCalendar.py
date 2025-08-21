#!/usr/bin/env python3
import json
from datetime import datetime
from collections import defaultdict
import html
from pathlib import Path
import re

INPUT_FILE = "upcoming_events.json"
OUTPUT_FILE = "eventsplain.html"


def parse_dt(iso_str: str) -> datetime:
    """
    Accepts:
      2025-08-18T09:00:00-0400
      2025-08-18T09:00:00-04:00
      2025-08-18T09:00:00.000-04:00
      2025-08-18T09:00:00Z
    """
    s = iso_str.strip().replace("Z", "+00:00")

    # Normalize trailing timezone offset to ±HH:MM (adds a colon if missing)
    # Matches ...+HHMM or ...-HHMM at end of string
    s = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", s)

    # If fractional seconds are >6 digits, truncate to microseconds
    m = re.match(r"^(.*\.\d+)([+-]\d{2}:\d{2})$", s)
    if m:
        head, tz = m.groups()
        pre, frac = head.split(".", 1)
        frac = (frac + "000000")[:6]  # pad/truncate to 6
        s = f"{pre}.{frac}{tz}"

    return datetime.fromisoformat(s)

def nice_date(dt: datetime) -> str:
    # Example: Wednesday, August 13, 2025
    return dt.strftime("%A, %B %-d, %Y") if "%" in "%-" else dt.strftime("%A, %B %d, %Y")

def nice_time(dt: datetime) -> str:
    # Example: 6:00 PM (strip leading zero)
    t = dt.strftime("%I:%M %p")
    return t.lstrip("0")

def format_description(text: str) -> str:
    escaped = html.escape(text or "")
    parts = [p.strip() for p in escaped.split("\n\n")]
    if len(parts) > 1:
        return "".join("<p>{}</p>".format(p.replace("\n", "<br>")) for p in parts if p)
    else:
        return "<p>{}</p>".format(escaped.replace("\n", "<br>")) if escaped else ""

def build_html(grouped, title="Upcoming Events"):
    # Inline CSS, Google Fonts link is CSS-only (no JS).
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #ffffff;
    --fg: #111111;
    --muted: #555555;
    --link: #000000; /* black links as requested */
    --card: #f7f7f7;
    --maxw: 950px;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{
    margin: 0;
    background: var(--bg);
    color: var(--fg);
    font-family: "Playfair Display", Georgia, "Times New Roman", serif;
    line-height: 1.6;
  }}
  .wrap {{
    width: 100%;
    padding: 1rem;            /* mobile: full width, modest padding */
  }}
  @media (min-width: 900px) {{
    .wrap {{
      max-width: var(--maxw); /* desktop: comfy centered column */
      margin: 0 auto;
      padding: 2.5rem 2rem;
    }}
  }}
  header.site {{
    margin-bottom: 1.25rem;
    border-bottom: 2px solid #e4e4e4;
    padding-bottom: .5rem;
  }}
  header.site h1 {{
    margin: 0;
    font-weight: 600;
    letter-spacing: .2px;
  }}
  .date-head {{
    margin: 2rem 0 1rem;
    padding-top: .5rem;
    border-top: 1px solid #ececec;
    font-size: 1.25rem;
    font-weight: 600;
  }}
  .event {{
    background: var(--card);
    border-radius: 14px;
    padding: 1rem;
    margin: .75rem 0;
  }}
  .event-time {{
    font-size: .95rem;
    font-weight: 600;
    color: var(--muted);
    margin-bottom: .25rem;
  }}
  .event-title a {{
    color: var(--link);       /* black link */
    text-decoration: none;
    font-weight: 600;
    font-size: 1.05rem;
  }}
  .event-title a:hover, .event-title a:focus {{
    text-decoration: underline;
  }}
  .event-desc p {{
    margin: .5rem 0 0;
  }}
  .location {{
    margin-top: .35rem;
    font-size: .9rem;
    color: var(--muted);
  }}
</style>
</head>
<body>
  <div class="wrap">
    <header class="site">
      <h1>{html.escape(title)}</h1>
    </header>
    {build_body(grouped)}
  </div>
</body>
</html>
"""

def build_body(grouped):
    chunks = []
    # grouped is Ordered by date externally; we’ll iterate in that order
    for date_key in grouped:
        human = nice_date(grouped[date_key][0]["_dt"])  # any event's dt
        chunks.append(f'<h2 class="date-head">{html.escape(human)}</h2>')
        for ev in grouped[date_key]:
            time_str = nice_time(ev["_dt"])
            name = html.escape(ev.get("name", "Untitled"))
            url = html.escape(ev.get("url") or "#")
            desc_html = format_description(ev.get("description", ""))
            loc = ev.get("location") or {}
            loc_str = ", ".join(filter(None, [loc.get("name"), loc.get("address")])) if isinstance(loc, dict) else ""
            loc_html = f'<div class="location">{html.escape(loc_str)}</div>' if loc_str else ""
            chunks.append(
                f'''<article class="event">
  <div class="event-time">{time_str}</div>
  <div class="event-title"><a href="{url}" target="_blank" rel="noopener">{name}</a></div>
  <div class="event-desc">{desc_html}</div>
  {loc_html}
</article>'''
            )
    return "\n".join(chunks)

import os
def main(city="baltimore"):
    data = json.loads(Path(os.path.join(city, INPUT_FILE)).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit("Expected a JSON array of events.")

    # Ensure each event has parsed datetime and keep stable order
    events = []
    for ev in data:
        sd = ev.get("startDate")
        if not sd:
            # skip items with no startDate
            continue
        dt = parse_dt(sd)
        ecopy = dict(ev)
        ecopy["_dt"] = dt
        events.append(ecopy)

    # They’re already ordered by date, but we’ll sort defensively by start datetime
    events.sort(key=lambda e: e["_dt"])

    # Group by calendar date (offset-aware datetime -> local date from the offset)
    grouped = defaultdict(list)
    order = []  # maintain insertion order of dates
    for ev in events:
        key = ev["_dt"].date().isoformat()
        if key not in grouped:
            order.append(key)
        grouped[key].append(ev)

    # Build an ordered dict-like iteration using order list
    ordered_grouped = {k: grouped[k] for k in order}

    html_str = build_html(ordered_grouped, title="Upcoming Events")
    Path(os.path.join(city, OUTPUT_FILE)).write_text(html_str, encoding="utf-8")
    print(f"Wrote {OUTPUT_FILE} with {len(events)} event(s).")

if __name__ == "__main__":
    main()
