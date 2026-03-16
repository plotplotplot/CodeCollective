import scrape_ics


ICS_URL = "https://bluewaterbaltimore.org/events/?ical=1"
EVENT_URL = "https://bluewaterbaltimore.org/baltimore-events/"
IMAGE_URL = "https://bluewaterbaltimore.org/wp-content/uploads/2023/09/BWB_Logo_Horizontal.png"


def scrape_events(city="baltimore"):
    return scrape_ics.fetch_calendar_events(
        ICS_URL=ICS_URL,
        city=city,
        imageURL=IMAGE_URL,
        eventUrl=EVENT_URL,
        recurring=False,
        preface="",
    )
