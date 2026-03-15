import importlib
from pathlib import Path
import sys

CITY_DIR = Path(__file__).resolve().parent
ROOT_DIR = CITY_DIR.parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import scrape_ics
import scrape_mtc


def collect_events(city="baltimore"):
    new_events = []

    scrape_gbc = importlib.import_module("baltimore.scrape_gbc")
    new_events += scrape_gbc.scrape_gbc_events()

    try:
        new_events += scrape_ics.fetch_calendar_events(
            ICS_URL="http://www.google.com/calendar/ical/baltimorenode.org_5jbobahkshgj11vut3cndhppoo%40group.calendar.google.com/public/basic.ics",
            imageURL="https://www.baltimorenode.org/wp-content/uploads/2013/11/node-logo.png",
            city=city,
            eventUrl="https://baltimorenode.org/events/",
            preface="Node ",
        )
    except Exception as e:
        print(f"Error fetching calendar events: {e}")

    try:
        scrape_tedco = importlib.import_module("baltimore.scrape_tedco")
        new_events += scrape_tedco.scrape_tedco_events(months=2)
    except Exception:
        print("Error fetching tedco")

    try:
        scrape_baltsistercities = importlib.import_module("baltimore.scrape_baltsistercities")
        new_events += scrape_baltsistercities.scrape_baltimore_events()
    except Exception:
        print("Error fetching Sister Cities")

    try:
        new_events += scrape_mtc.scrape_mtc_events()
    except Exception:
        print("Error fetching MTC")

    try:
        new_events += scrape_ics.fetch_calendar_events(
            ICS_URL="https://calendar.google.com/calendar/ical/unallocatedspacehq@gmail.com/public/basic.ics",
            imageURL="https://www.unallocatedspace.org/wp-content/uploads/2017/03/UnallocatedLogoSmall.png",
            city=city,
            eventUrl="https://www.unallocatedspace.org/events/",
            preface="UAS ",
        )
    except Exception as e:
        print(f"Error fetching calendar events: {e}")

    try:
        new_events += scrape_ics.processICS(
            CACHE_FILENAME="maryland-stem-festival-96ecc18ef7d.ics",
            imageURL="https://marylandstemfestival.org/wp-content/uploads/2024/06/Family-Feud-group-Pix-1-scaled-e1717876361661.jpeg",
            eventUrl="https://marylandstemfestival.org/events/month/",
            preface="STEMFest ",
        )
    except Exception as e:
        print(f"Error fetching calendar events: {e}")

    try:
        new_events += scrape_ics.fetch_calendar_events(
            ICS_URL="https://baltimoreindiegames.com/events/list/?ical=1",
            imageURL="https://baltimoreindiegames.com/wp-content/uploads/2025/03/BIG_small.png",
            eventUrl="https://baltimoreindiegames.com/events/",
            city="baltimore",
            preface="",
            recurring=False,
        )
    except Exception as e:
        print(f"Error fetching calendar events: {e}")

    try:
        new_events += scrape_ics.fetch_calendar_events(
            ICS_URL="https://calendar.google.com/calendar/ical/c_be274545c6e9af174fab0df99319a3c47f1be77a013450babf6d03e90396a064%40group.calendar.google.com/public/basic.ics",
            city=city,
            imageURL="https://static.wixstatic.com/media/8dc51b_7123df01d68e47a1b4b717c89ad4aea7~mv2.png/v1/fill/w_223,h_90,al_c,q_85,usm_0.66_1.00_0.01,enc_avif,quality_auto/BDEC%20(1).png",
            eventUrl="https://www.digitalequitybaltimore.org/general-clean",
            recurring=False,
            preface="",
        )
    except Exception as e:
        print(f"Error fetching calendar events: {e}")

    try:
        new_events += scrape_ics.fetch_calendar_events(
            ICS_URL="https://calendar.google.com/calendar/ical/c_35ce051bfecc3ebd59f7776829ca549d2dd38e8ab2a50b07bd4243cb1c218c72%40group.calendar.google.com/public/basic.ics",
            city=city,
            imageURL="https://chesapeakeclimate.org/wp-content/uploads/2022/02/CCAN-Logo-2022-300RGB-wht-e1643743097559.png",
            eventUrl="https://calendar.google.com/calendar/u/0/r?cid=c_35ce051bfecc3ebd59f7776829ca549d2dd38e8ab2a50b07bd4243cb1c218c72@group.calendar.google.com",
            recurring=False,
            preface="",
        )
    except Exception as e:
        print(f"Error fetching custom Google calendar events: {e}")

    try:
        scrape_spark = importlib.import_module("baltimore.scrape_spark")
        new_events += scrape_spark.scrape_spark_events()
    except Exception as e:
        print(f"Error fetching calendar events: {e}")

    try:
        scrape_bwtech = importlib.import_module("baltimore.scrape_bwtech")
        new_events += scrape_bwtech.scrape_events()
    except Exception as e:
        print(f"Error fetching calendar events: {e}")

    try:
        scrape_startup = importlib.import_module("baltimore.scrape_starTUp")
        new_events += scrape_startup.scrape_towson_events()
    except Exception as e:
        print(f"Error fetching calendar events: {e}")

    try:
        scrape_innovatemd = importlib.import_module("baltimore.scrape_innovatemd")
        new_events += scrape_innovatemd.scrape_all()
    except Exception as e:
        print(f"Error fetching calendar events: {e}")

    try:
        scrape_wssc = importlib.import_module("baltimore.scrape_wssc")
        new_events += scrape_wssc.scrape_all_wssc_events()
    except Exception as e:
        print(f"Error fetching WSSC events: {e}")

    return new_events
