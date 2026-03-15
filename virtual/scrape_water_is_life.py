from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Dict, List

import requests


HOME_URL = "https://waterislifeschools.com/"
IMAGE_URL = "https://waterislifeschools.com/wp-content/uploads/2021/06/logo-Maurick.jpeg"


def scrape_events() -> List[Dict[str, object]]:
    response = requests.get(HOME_URL, timeout=30)
    response.raise_for_status()
    html = response.text
    scraped_at = datetime.now().isoformat()

    match = re.search(
        r"WATER IS LIFE\s+2026.*?June\s+8-12,\s+2026.*?Maurick College.*?Vught,\s+the Netherlands",
        html,
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return []

    return [
        {
            "id": hashlib.md5(HOME_URL.encode()).hexdigest()[:16],
            "name": "Water Is Life 2026",
            "startDate": "2026-06-08T00:00:00+00:00",
            "endTime": "2026-06-12T23:59:00+00:00",
            "description": "Water Is Life 2026 conference hosted by Maurick College in Vught, the Netherlands.",
            "url": HOME_URL,
            "status": "ACTIVE",
            "location": {
                "name": "Maurick College",
                "address": "Vught, the Netherlands",
            },
            "imageUrl": IMAGE_URL,
            "recurring": False,
            "scrapeTime": scraped_at,
        }
    ]
