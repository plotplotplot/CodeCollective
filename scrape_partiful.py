import json
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from http_client import build_session, polite_get


def _extract_event_id(url: str) -> str:
    try:
        path_segments = [segment for segment in urlparse(url).path.split("/") if segment]
    except Exception:
        return ""

    if len(path_segments) >= 2 and path_segments[0] == "e":
        return path_segments[1]
    return ""


def _pick_event_schema(data):
    if isinstance(data, dict):
        if data.get("@type") == "Event":
            return data
        graph = data.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                if isinstance(item, dict) and item.get("@type") == "Event":
                    return item
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and item.get("@type") == "Event":
                return item
    return None


def _parse_ldjson_event(soup: BeautifulSoup):
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text() or ""
        raw = raw.strip()
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue

        event_schema = _pick_event_schema(parsed)
        if event_schema:
            return event_schema

    return None


def _parse_next_data_event(soup: BeautifulSoup):
    script = soup.find("script", attrs={"id": "__NEXT_DATA__", "type": "application/json"})
    if not script:
        return {}

    raw = script.string or script.get_text() or ""
    if not raw.strip():
        return {}

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}

    return (
        parsed.get("props", {})
        .get("pageProps", {})
        .get("event", {})
    )


def _status_from_schema(schema_status: str, next_status: str):
    schema_status = (schema_status or "").lower()
    if "eventcancelled" in schema_status:
        return "CANCELLED"
    if "eventpostponed" in schema_status:
        return "POSTPONED"

    next_status = (next_status or "").upper()
    if next_status in {"CANCELLED", "POSTPONED", "DRAFT"}:
        return next_status

    return "ACTIVE"


def _fetch_html(url: str, headers: dict):
    session = build_session()
    try:
        response = polite_get(session, url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception:
        return ""


def parse_partiful_event(url: str, html_content: str = ""):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    html = html_content or _fetch_html(url, headers)
    if not html:
        print("Failed to retrieve Partiful page")
        return []

    soup = BeautifulSoup(html, "html.parser")
    event_schema = _parse_ldjson_event(soup) or {}
    next_event = _parse_next_data_event(soup) or {}

    canonical_tag = soup.find("link", attrs={"rel": "canonical"})
    canonical_url = canonical_tag.get("href") if canonical_tag else ""

    title = (
        event_schema.get("name")
        or next_event.get("title")
        or (soup.title.text.strip() if soup.title else "")
    )

    description = (
        event_schema.get("description")
        or next_event.get("description")
        or ""
    )

    start_date = event_schema.get("startDate") or next_event.get("startDate")
    end_time = event_schema.get("endDate") or next_event.get("endDate")
    timezone = next_event.get("timezone") or ""

    image_url = event_schema.get("image")
    if isinstance(image_url, list):
        image_url = image_url[0] if image_url else ""
    if not image_url:
        og_image = soup.find("meta", attrs={"property": "og:image"})
        image_url = og_image.get("content") if og_image else ""

    location = {}
    schema_location = event_schema.get("location")
    if isinstance(schema_location, dict):
        location_name = schema_location.get("name") or ""
        location["name"] = location_name
        address = schema_location.get("address")
        if isinstance(address, dict):
            location["address"] = address.get("streetAddress") or ""
            location["city"] = address.get("addressLocality") or ""
            location["state"] = address.get("addressRegion") or ""
            location["country"] = address.get("addressCountry") or ""
        elif isinstance(address, str):
            location["address"] = address

    if not location:
        location_info = next_event.get("locationInfo") or {}
        location_value = location_info.get("value") if isinstance(location_info, dict) else ""
        if location_value:
            location = {"name": location_value, "address": location_value}

    organizer = event_schema.get("organizer")
    host_name = ""
    if isinstance(organizer, list) and organizer:
        first_org = organizer[0]
        if isinstance(first_org, dict):
            host_name = first_org.get("name") or ""
    elif isinstance(organizer, dict):
        host_name = organizer.get("name") or ""

    if not host_name:
        hosts = next_event.get("hosts") or []
        if isinstance(hosts, list) and hosts:
            first_host = hosts[0]
            if isinstance(first_host, dict):
                host_name = first_host.get("name") or ""

    event_id = next_event.get("id") or _extract_event_id(canonical_url or url)
    clean_url = canonical_url or url.split("?")[0]

    if not title or not start_date:
        print("Partiful scraper: missing required fields (title/startDate)")
        return []

    return [
        {
            "id": event_id,
            "name": title,
            "description": description,
            "startDate": start_date,
            "endTime": end_time,
            "timezone": timezone,
            "url": clean_url,
            "status": _status_from_schema(event_schema.get("eventStatus", ""), next_event.get("status", "")),
            "location": location,
            "imageUrl": image_url,
            "source_group": host_name,
        }
    ]


if __name__ == "__main__":
    sample_url = "https://partiful.com/e/IjvnMmmJOBBvkAIsYjTN"
    print(json.dumps(parse_partiful_event(sample_url), indent=2))
