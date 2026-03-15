import importlib
from pathlib import Path
import sys

CITY_DIR = Path(__file__).resolve().parent
ROOT_DIR = CITY_DIR.parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import scrape_ics
import scrape_mtc


def merge_tags(*tag_lists):
    merged = []
    seen = set()

    for tag_list in tag_lists:
        if not tag_list:
            continue
        for tag in tag_list:
            if not tag or tag in seen:
                continue
            seen.add(tag)
            merged.append(tag)

    return merged


def apply_source_tags(events, source_url, source_tags):
    if not events:
        return []

    normalized_events = events if isinstance(events, list) else [events]
    for event in normalized_events:
        if not isinstance(event, dict):
            continue
        event["tags"] = merge_tags(source_tags, event.get("tags"))
        if source_url:
            event.setdefault("source", source_url)
            event["source_url"] = source_url

    return normalized_events


def collect_events(city="baltimore", error_logger=None):
    new_events = []

    def log_error(message, error, source_url=None, scraper=None):
        print(f"{message}: {error}")
        if error_logger:
            error_logger(
                stage="city_collect",
                error=error,
                source_url=source_url,
                scraper=scraper,
            )

    scrape_gbc = importlib.import_module("baltimore.scrape_gbc")
    new_events += apply_source_tags(
        scrape_gbc.scrape_gbc_events(),
        "https://gbc.org/events/",
        ["Business"],
    )

    try:
        new_events += apply_source_tags(scrape_ics.fetch_calendar_events(
            ICS_URL="http://www.google.com/calendar/ical/baltimorenode.org_5jbobahkshgj11vut3cndhppoo%40group.calendar.google.com/public/basic.ics",
            imageURL="https://www.baltimorenode.org/wp-content/uploads/2013/11/node-logo.png",
            city=city,
            eventUrl="https://baltimorenode.org/events/",
            preface="Node ",
        ), "https://baltimorenode.org/events/", ["Tech Skills"])
    except Exception as e:
        log_error("Error fetching calendar events", e, "https://baltimorenode.org/events/", "scrape_ics.fetch_calendar_events")

    try:
        new_events += apply_source_tags(scrape_ics.fetch_calendar_events(
            ICS_URL="https://catonsvillepres.org/events/?ical=1",
            imageURL="https://catonsvillepres.org/wp-content/uploads/2023/02/social-sharing.png",
            city=city,
            eventUrl="https://catonsvillepres.org/events/",
            preface="",
        ), "https://catonsvillepres.org/events/", ["Religion"])
    except Exception as e:
        log_error("Error fetching Catonsville Presbyterian events", e, "https://catonsvillepres.org/events/", "scrape_ics.fetch_calendar_events")

    try:
        new_events += apply_source_tags(scrape_ics.fetch_calendar_events(
            ICS_URL="https://calendar.google.com/calendar/ical/daraltaqwamd%40gmail.com/public/basic.ics",
            imageURL="https://taqwa.net/wp-content/uploads/2023/03/logo-w.png",
            city=city,
            eventUrl="https://taqwa.net/events/",
            preface="",
        ), "https://taqwa.net/events/", ["Religion"])
    except Exception as e:
        log_error("Error fetching Dar Al-Taqwa events", e, "https://taqwa.net/events/", "scrape_ics.fetch_calendar_events")

    try:
        new_events += apply_source_tags(scrape_ics.fetch_calendar_events(
            ICS_URL="https://ggwo.org/gg-events/?ical=1",
            imageURL="https://ggwo.org/wp-content/uploads/2018/11/ggwo-logo-with-world-wide-local-church-800-162-png1.png",
            city=city,
            eventUrl="https://ggwo.org/gg-events/",
            preface="",
        ), "https://ggwo.org/gg-events/", ["Religion"])
    except Exception as e:
        log_error("Error fetching GGWO events", e, "https://ggwo.org/gg-events/", "scrape_ics.fetch_calendar_events")

    try:
        new_events += apply_source_tags(scrape_ics.fetch_calendar_events(
            ICS_URL="https://incarnationbmore.org/events/?ical=1",
            imageURL="https://incarnationbmore.org/wp-content/uploads/2022/09/Incarnation-Logo-Words-Color.png",
            city=city,
            eventUrl="https://incarnationbmore.org/events/",
            preface="",
        ), "https://incarnationbmore.org/events/", ["Religion"])
    except Exception as e:
        log_error("Error fetching Cathedral of the Incarnation events", e, "https://incarnationbmore.org/events/", "scrape_ics.fetch_calendar_events")

    try:
        scrape_catonsvilleumc = importlib.import_module("baltimore.scrape_catonsvilleumc")
        new_events += apply_source_tags(
            scrape_catonsvilleumc.scrape_events(),
            "https://www.catonsvilleumc.org/upcoming-events/",
            ["Religion"],
        )
    except Exception as e:
        log_error("Error fetching Catonsville UMC events", e, "https://www.catonsvilleumc.org/upcoming-events/", "baltimore.scrape_catonsvilleumc")

    try:
        scrape_saintmos = importlib.import_module("baltimore.scrape_saintmos")
        new_events += apply_source_tags(
            scrape_saintmos.scrape_events(),
            "https://saintmos.org/gatherings",
            ["Religion"],
        )
    except Exception as e:
        log_error("Error fetching St. Moses events", e, "https://saintmos.org/gatherings", "baltimore.scrape_saintmos")

    try:
        scrape_haic = importlib.import_module("baltimore.scrape_haic")
        new_events += apply_source_tags(
            scrape_haic.scrape_events(),
            "https://haicbaltimore.org/upcoming-events/",
            ["Religion"],
        )
    except Exception as e:
        log_error("Error fetching HAIC events", e, "https://haicbaltimore.org/upcoming-events/", "baltimore.scrape_haic")

    try:
        scrape_rccbaltimore = importlib.import_module("baltimore.scrape_rccbaltimore")
        new_events += apply_source_tags(
            scrape_rccbaltimore.scrape_events(),
            "https://www.rccbaltimore.org/events-1",
            ["Religion"],
        )
    except Exception as e:
        log_error("Error fetching Redemption City Church events", e, "https://www.rccbaltimore.org/events-1", "baltimore.scrape_rccbaltimore")

    try:
        new_events += apply_source_tags(scrape_ics.fetch_calendar_events(
            ICS_URL="https://jagganathtemple.org/events/?ical=1",
            imageURL="https://jagganathtemple.org/wp-content/uploads/2025/11/cropped-Jagannath-Temple-of-North-America-1.png",
            city=city,
            eventUrl="https://jagganathtemple.org/events/",
            preface="",
        ), "https://jagganathtemple.org/events/", ["Religion"])
    except Exception as e:
        log_error("Error fetching Jagannath Temple events", e, "https://jagganathtemple.org/events/", "scrape_ics.fetch_calendar_events")

    try:
        scrape_columbiapres = importlib.import_module("baltimore.scrape_columbiapres")
        new_events += apply_source_tags(
            scrape_columbiapres.scrape_events(),
            "https://columbiapres.org/",
            ["Religion"],
        )
    except Exception as e:
        log_error("Error fetching Columbia Presbyterian events", e, "https://columbiapres.org/", "baltimore.scrape_columbiapres")

    try:
        scrape_mosaicchristian = importlib.import_module("baltimore.scrape_mosaicchristian")
        new_events += apply_source_tags(
            scrape_mosaicchristian.scrape_events(),
            "https://mosaicchristian.org/events/",
            ["Religion"],
        )
    except Exception as e:
        log_error("Error fetching Mosaic Christian events", e, "https://mosaicchristian.org/events/", "baltimore.scrape_mosaicchristian")

    try:
        scrape_calvaryec = importlib.import_module("baltimore.scrape_calvaryec")
        new_events += apply_source_tags(
            scrape_calvaryec.scrape_events(),
            "https://calvaryec.com/events",
            ["Religion"],
        )
    except Exception as e:
        log_error("Error fetching Calvary Chapel Ellicott City events", e, "https://calvaryec.com/events", "baltimore.scrape_calvaryec")

    try:
        scrape_mtzion = importlib.import_module("baltimore.scrape_mtzion")
        new_events += apply_source_tags(
            scrape_mtzion.scrape_events(),
            "https://www.mtzionbaltimore.org/events/",
            ["Religion"],
        )
    except Exception as e:
        log_error("Error fetching Mt. Zion Church events", e, "https://www.mtzionbaltimore.org/events/", "baltimore.scrape_mtzion")

    try:
        scrape_firstpreshc = importlib.import_module("baltimore.scrape_firstpreshc")
        new_events += apply_source_tags(
            scrape_firstpreshc.scrape_events(),
            "https://www.firstpreshc.org/worship",
            ["Religion"],
        )
    except Exception as e:
        log_error("Error fetching First Presbyterian Howard County events", e, "https://www.firstpreshc.org/worship", "baltimore.scrape_firstpreshc")

    try:
        scrape_bridgeway = importlib.import_module("baltimore.scrape_bridgeway")
        new_events += apply_source_tags(
            scrape_bridgeway.scrape_events(),
            "https://bridgeway.cc/services",
            ["Religion"],
        )
    except Exception as e:
        log_error("Error fetching Bridgeway events", e, "https://bridgeway.cc/services", "baltimore.scrape_bridgeway")

    try:
        scrape_gardenchurch = importlib.import_module("baltimore.scrape_gardenchurch")
        new_events += apply_source_tags(
            scrape_gardenchurch.scrape_events(),
            "https://www.thegardenbaltimore.com/",
            ["Religion"],
        )
    except Exception as e:
        log_error("Error fetching The Garden Church events", e, "https://www.thegardenbaltimore.com/", "baltimore.scrape_gardenchurch")

    try:
        scrape_tedco = importlib.import_module("baltimore.scrape_tedco")
        new_events += apply_source_tags(
            scrape_tedco.scrape_tedco_events(months=2),
            "https://www.tedcomd.com/events/",
            ["Economic Development"],
        )
    except Exception as e:
        log_error("Error fetching tedco", e, "https://www.tedcomd.com/events/", "baltimore.scrape_tedco")

    try:
        scrape_baltsistercities = importlib.import_module("baltimore.scrape_baltsistercities")
        new_events += apply_source_tags(
            scrape_baltsistercities.scrape_baltimore_events(),
            "https://baltimoresistercities.org/events/",
            ["Community", "Culture"],
        )
    except Exception as e:
        log_error("Error fetching Sister Cities", e, "https://baltimoresistercities.org/events/", "baltimore.scrape_baltsistercities")

    try:
        new_events += apply_source_tags(
            scrape_mtc.scrape_mtc_events(),
            "https://members.mdtechcouncil.com/eventcalendar",
            ["Business"],
        )
    except Exception as e:
        log_error("Error fetching MTC", e, "https://members.mdtechcouncil.com/eventcalendar", "scrape_mtc.scrape_mtc_events")

    try:
        new_events += apply_source_tags(scrape_ics.fetch_calendar_events(
            ICS_URL="https://calendar.google.com/calendar/ical/unallocatedspacehq@gmail.com/public/basic.ics",
            imageURL="https://www.unallocatedspace.org/wp-content/uploads/2017/03/UnallocatedLogoSmall.png",
            city=city,
            eventUrl="https://www.unallocatedspace.org/events/",
            preface="UAS ",
        ), "https://www.unallocatedspace.org/events/", ["Makerspace"])
    except Exception as e:
        log_error("Error fetching calendar events", e, "https://www.unallocatedspace.org/events/", "scrape_ics.fetch_calendar_events")

    try:
        new_events += apply_source_tags(scrape_ics.processICS(
            CACHE_FILENAME="maryland-stem-festival-96ecc18ef7d.ics",
            imageURL="https://marylandstemfestival.org/wp-content/uploads/2024/06/Family-Feud-group-Pix-1-scaled-e1717876361661.jpeg",
            eventUrl="https://marylandstemfestival.org/events/month/",
            preface="STEMFest ",
        ), "https://marylandstemfestival.org/events/month/", ["Tech Skills"])
    except Exception as e:
        log_error("Error fetching calendar events", e, "https://marylandstemfestival.org/events/month/", "scrape_ics.processICS")

    try:
        new_events += apply_source_tags(scrape_ics.fetch_calendar_events(
            ICS_URL="https://baltimoreindiegames.com/events/list/?ical=1",
            imageURL="https://baltimoreindiegames.com/wp-content/uploads/2025/03/BIG_small.png",
            eventUrl="https://baltimoreindiegames.com/events/",
            city="baltimore",
            preface="",
            recurring=False,
        ), "https://baltimoreindiegames.com/events/", ["Makerspace"])
    except Exception as e:
        log_error("Error fetching calendar events", e, "https://baltimoreindiegames.com/events/", "scrape_ics.fetch_calendar_events")

    try:
        new_events += apply_source_tags(scrape_ics.fetch_calendar_events(
            ICS_URL="https://calendar.google.com/calendar/ical/c_be274545c6e9af174fab0df99319a3c47f1be77a013450babf6d03e90396a064%40group.calendar.google.com/public/basic.ics",
            city=city,
            imageURL="https://static.wixstatic.com/media/8dc51b_7123df01d68e47a1b4b717c89ad4aea7~mv2.png/v1/fill/w_223,h_90,al_c,q_85,usm_0.66_1.00_0.01,enc_avif,quality_auto/BDEC%20(1).png",
            eventUrl="https://www.digitalequitybaltimore.org/general-clean",
            recurring=False,
            preface="",
        ), "https://www.digitalequitybaltimore.org/general-clean", ["Economic Development"])
    except Exception as e:
        log_error("Error fetching calendar events", e, "https://www.digitalequitybaltimore.org/general-clean", "scrape_ics.fetch_calendar_events")

    try:
        new_events += apply_source_tags(scrape_ics.fetch_calendar_events(
            ICS_URL="https://calendar.google.com/calendar/ical/c_35ce051bfecc3ebd59f7776829ca549d2dd38e8ab2a50b07bd4243cb1c218c72%40group.calendar.google.com/public/basic.ics",
            city=city,
            imageURL="https://chesapeakeclimate.org/wp-content/uploads/2022/02/CCAN-Logo-2022-300RGB-wht-e1643743097559.png",
            eventUrl="https://calendar.google.com/calendar/u/0/r?cid=c_35ce051bfecc3ebd59f7776829ca549d2dd38e8ab2a50b07bd4243cb1c218c72@group.calendar.google.com",
            recurring=False,
            preface="",
        ), "https://calendar.google.com/calendar/u/0/r?cid=c_35ce051bfecc3ebd59f7776829ca549d2dd38e8ab2a50b07bd4243cb1c218c72@group.calendar.google.com", ["Water"])
    except Exception as e:
        log_error("Error fetching custom Google calendar events", e, "https://calendar.google.com/calendar/u/0/r?cid=c_35ce051bfecc3ebd59f7776829ca549d2dd38e8ab2a50b07bd4243cb1c218c72@group.calendar.google.com", "scrape_ics.fetch_calendar_events")

    try:
        scrape_spark = importlib.import_module("baltimore.scrape_spark")
        new_events += apply_source_tags(
            scrape_spark.scrape_spark_events(),
            "https://sparkcoworking.com/baltimore/",
            ["Economic Development"],
        )
    except Exception as e:
        print(f"Error fetching calendar events: {e}")

    try:
        scrape_bwtech = importlib.import_module("baltimore.scrape_bwtech")
        new_events += apply_source_tags(
            scrape_bwtech.scrape_events(),
            "https://bwtech.umbc.edu/events/",
            ["Economic Development"],
        )
    except Exception as e:
        print(f"Error fetching calendar events: {e}")

    try:
        scrape_startup = importlib.import_module("baltimore.scrape_starTUp")
        new_events += apply_source_tags(
            scrape_startup.scrape_towson_events(),
            "https://www.towson.edu/startup/about/events.html",
            ["Business"],
        )
    except Exception as e:
        print(f"Error fetching calendar events: {e}")

    try:
        scrape_innovatemd = importlib.import_module("baltimore.scrape_innovatemd")
        new_events += apply_source_tags(
            scrape_innovatemd.scrape_all(),
            "https://innovationmaryland.org/events/",
            ["Economic Development"],
        )
    except Exception as e:
        print(f"Error fetching calendar events: {e}")

    try:
        scrape_wssc = importlib.import_module("baltimore.scrape_wssc")
        new_events += apply_source_tags(
            scrape_wssc.scrape_all_wssc_events(),
            "https://www.wsscwater.com/events",
            ["Water"],
        )
    except Exception as e:
        print(f"Error fetching WSSC events: {e}")

    try:
        scrape_bluewaterbaltimore = importlib.import_module("baltimore.scrape_bluewaterbaltimore")
        new_events += apply_source_tags(
            scrape_bluewaterbaltimore.scrape_events(city=city),
            "https://bluewaterbaltimore.org/events/",
            ["Water"],
        )
    except Exception as e:
        print(f"Error fetching Blue Water Baltimore events: {e}")

    try:
        scrape_waterfrontpartnership = importlib.import_module("baltimore.scrape_waterfrontpartnership")
        new_events += apply_source_tags(
            scrape_waterfrontpartnership.scrape_events(),
            "https://waterfrontpartnership.org/events/",
            ["Culture"],
        )
    except Exception as e:
        print(f"Error fetching Waterfront Partnership events: {e}")

    try:
        scrape_chesapeakewea = importlib.import_module("baltimore.scrape_chesapeakewea")
        new_events += apply_source_tags(
            scrape_chesapeakewea.scrape_events(),
            "https://chesapeakewea.org/events/",
            ["Water"],
        )
    except Exception as e:
        print(f"Error fetching Chesapeake WEA events: {e}")

    try:
        scrape_csawwa = importlib.import_module("baltimore.scrape_csawwa")
        new_events += apply_source_tags(
            scrape_csawwa.scrape_events(),
            "https://csawwa.org/events/",
            ["Water"],
        )
    except Exception as e:
        print(f"Error fetching CSAWWA events: {e}")

    return new_events
