from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List

from dateutil import parser as date_parser

from http_client import build_session, polite_get


TEAM_ID = 110  # Baltimore Orioles
SCHEDULE_API = "https://statsapi.mlb.com/api/v1/schedule"
TEAM_PAGE_URL = "https://www.mlb.com/orioles/schedule"


def _safe_parse_iso(value: str) -> str:
    dt = date_parser.parse(value)
    return dt.isoformat()


def scrape_events(lookahead_days: int = 210) -> List[Dict]:
    session = build_session()
    today = datetime.now().date()
    end_date = today + timedelta(days=lookahead_days)

    params = {
        "sportId": 1,
        "teamId": TEAM_ID,
        "startDate": today.isoformat(),
        "endDate": end_date.isoformat(),
    }

    resp = polite_get(session, SCHEDULE_API, params=params, timeout=30)
    resp.raise_for_status()
    payload = resp.json() if resp.content else {}

    events: List[Dict] = []
    seen = set()
    for date_block in payload.get("dates", []):
        for game in date_block.get("games", []):
            game_pk = game.get("gamePk")
            game_date = game.get("gameDate")
            teams = game.get("teams", {})
            home = (teams.get("home") or {}).get("team", {}) or {}
            away = (teams.get("away") or {}).get("team", {}) or {}
            venue = game.get("venue") or {}

            if not game_pk or not game_date:
                continue

            try:
                start_iso = _safe_parse_iso(str(game_date))
            except Exception:
                continue

            away_name = str(away.get("name") or "TBD").strip()
            home_name = str(home.get("name") or "Baltimore Orioles").strip()
            title = f"{away_name} at {home_name}"
            game_state = str(((game.get("status") or {}).get("detailedState") or "")).lower()
            status = "ACTIVE"
            if "cancel" in game_state:
                status = "CANCELLED"
            elif "postpon" in game_state:
                status = "POSTPONED"

            event_url = f"https://www.mlb.com/gameday/{game_pk}"
            key = (title.lower(), start_iso)
            if key in seen:
                continue
            seen.add(key)

            events.append(
                {
                    "name": title,
                    "description": f"Baltimore Orioles regular season game (Game {game_pk}).",
                    "startDate": start_iso,
                    "endTime": "",
                    "url": event_url,
                    "status": status,
                    "location": {
                        "name": str(venue.get("name") or "").strip(),
                        "address": str(venue.get("name") or "").strip(),
                    },
                    "source": TEAM_PAGE_URL,
                }
            )

    return events
