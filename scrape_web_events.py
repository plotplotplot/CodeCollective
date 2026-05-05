import json
from typing import Any, Dict, List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from http_client import build_session, polite_get


def _as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _normalize_event_schema(item: Dict[str, Any], source_url: str) -> Dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    item_type = item.get("@type")
    if isinstance(item_type, list):
        is_event = "Event" in item_type
    else:
        is_event = str(item_type or "").lower() == "event"
    if not is_event:
        return None

    name = str(item.get("name") or "").strip()
    start = str(item.get("startDate") or "").strip()
    if not name or not start:
        return None

    location = item.get("location") or {}
    loc_name = ""
    loc_addr = ""
    if isinstance(location, dict):
        loc_name = str(location.get("name") or "").strip()
        address = location.get("address")
        if isinstance(address, dict):
            loc_addr = str(
                address.get("streetAddress")
                or address.get("addressLocality")
                or address.get("name")
                or ""
            ).strip()
        elif isinstance(address, str):
            loc_addr = address.strip()
    elif isinstance(location, str):
        loc_name = location.strip()

    image = item.get("image")
    if isinstance(image, list):
        image = image[0] if image else ""
    image_url = str(image or "").strip()

    event_url = str(item.get("url") or item.get("@id") or "").strip()
    if event_url:
        event_url = urljoin(source_url, event_url)
    else:
        event_url = source_url

    status_raw = str(item.get("eventStatus") or "").lower()
    status = "ACTIVE" if ("cancel" not in status_raw and "postpon" not in status_raw) else "CANCELLED"

    return {
        "name": name,
        "description": str(item.get("description") or "").strip(),
        "startDate": start,
        "endTime": str(item.get("endDate") or "").strip(),
        "url": event_url,
        "status": status,
        "location": {"name": loc_name, "address": loc_addr},
        "imageUrl": image_url,
        "source": source_url,
    }


def _extract_events_from_jsonld_payload(payload: Any, source_url: str) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    if isinstance(payload, dict):
        maybe_graph = payload.get("@graph")
        if isinstance(maybe_graph, list):
            for node in maybe_graph:
                evt = _normalize_event_schema(node, source_url)
                if evt:
                    events.append(evt)
        evt = _normalize_event_schema(payload, source_url)
        if evt:
            events.append(evt)
        for item in _as_list(payload.get("itemListElement")):
            if isinstance(item, dict):
                evt = _normalize_event_schema(item.get("item") or item, source_url)
                if evt:
                    events.append(evt)
    elif isinstance(payload, list):
        for node in payload:
            events.extend(_extract_events_from_jsonld_payload(node, source_url))
    return events


def parse_web_events_page(source_url: str) -> List[Dict[str, Any]]:
    session = build_session()
    response = polite_get(session, source_url, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    events: List[Dict[str, Any]] = []
    seen = set()
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text() or ""
        raw = raw.strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for evt in _extract_events_from_jsonld_payload(payload, source_url):
            key = (evt.get("name", "").strip().lower(), evt.get("startDate", ""))
            if key in seen:
                continue
            seen.add(key)
            events.append(evt)
    return events
