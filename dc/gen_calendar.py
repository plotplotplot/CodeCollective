import importlib
from pathlib import Path
import sys

CITY_DIR = Path(__file__).resolve().parent
ROOT_DIR = CITY_DIR.parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def collect_events(city="dc", error_logger=None):
    new_events = []

    try:
        scrape_usgpo = importlib.import_module("dc.scrape_usgpo")
        new_events += scrape_usgpo.scrape_upcoming_events()
    except Exception as e:
        if error_logger:
            error_logger("city_collect", e, scraper="dc.scrape_usgpo")

    try:
        scrape_dcwater = importlib.import_module("dc.scrape_dcwater")
        new_events += scrape_dcwater.scrape_events()
    except Exception as e:
        if error_logger:
            error_logger("city_collect", e, scraper="dc.scrape_dcwater")

    return new_events
