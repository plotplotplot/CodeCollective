import importlib
from pathlib import Path
import sys

CITY_DIR = Path(__file__).resolve().parent
ROOT_DIR = CITY_DIR.parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def collect_events(city="dc"):
    new_events = []

    try:
        scrape_usgpo = importlib.import_module("dc.scrape_usgpo")
        new_events += scrape_usgpo.scrape_upcoming_events()
    except Exception:
        pass

    return new_events
