from city_source_taxonomy import apply_city_source_taxonomy

sources = [
    {
        "url": "https://www.eventbrite.com/o/techconnect-west-virginia-111407937521",
        "group_name": "TechConnect West Virginia",
        "tags": ["Tech Community", "Tech Skills"],
    },
]

apply_city_source_taxonomy(sources)
