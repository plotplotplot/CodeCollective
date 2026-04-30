from city_source_taxonomy import apply_city_source_taxonomy

# Add organizations here that host events across multiple city regions.
# Example:
# {
#     "url": "https://www.meetup.com/example-org/",
#     "group_name": "Example Org",
#     "tags": ["Tech Community", "Professional Networking"],
# }
sources = [
    {
        "url": "https://www.eventbrite.com/o/11206981546",
        "tags": ["Tech Community", "Professional Networking", "Career Growth"],
    },
]

apply_city_source_taxonomy(sources)
