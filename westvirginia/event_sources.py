sources = [
    {
        "url": "https://www.eventbrite.com/o/techconnect-west-virginia-111407937521",
        "group_name": "TechConnect West Virginia",
        "tags": ["Tech Community", "Tech Skills"],
    },
]

_MASLOW_BY_TAG = {
    "Food": ["Food"],
    "Water": ["Water"],
    "Water & Environment": ["Water"],
    "Housing": ["Shelter + Habitat", "Safety & Stability"],
    "Shelter + Habitat": ["Shelter + Habitat"],
    "Clothing": ["Clothing"],
    "Survival & Health": ["Survival & Health"],
    "Wellness": ["Survival & Health"],
    "Health": ["Survival & Health"],
    "Health & Wellness": ["Survival & Health"],
    "Safety & Stability": ["Safety & Stability"],
    "Infrastructure": ["Safety & Stability"],
    "Finance": ["Safety & Stability"],
    "Climate & Energy": ["Safety & Stability"],
    "Climate": ["Safety & Stability"],
    "Energy": ["Safety & Stability"],
    "Belonging & Culture": ["Belonging & Culture"],
    "Culture": ["Belonging & Culture"],
    "Community": ["Belonging & Culture"],
    "Religion": ["Belonging & Culture"],
    "Community Organizing": ["Belonging & Culture", "Purpose & Service"],
    "Tech Community": ["Belonging & Culture"],
    "Code Collective & Partners": ["Belonging & Culture"],
    "Esteem & Opportunity": ["Esteem & Opportunity"],
    "Economic Development": ["Esteem & Opportunity"],
    "Economics": ["Esteem & Opportunity"],
    "Business": ["Esteem & Opportunity"],
    "Startup": ["Esteem & Opportunity"],
    "Entrepreneurship": ["Esteem & Opportunity"],
    "Career Growth": ["Esteem & Opportunity"],
    "Professional Networking": ["Esteem & Opportunity"],
    "Growth & Creativity": ["Growth & Creativity"],
    "Tech Skills": ["Growth & Creativity"],
    "Education": ["Growth & Creativity"],
    "Science": ["Growth & Creativity"],
    "Lifelong Learning": ["Growth & Creativity"],
    "Youth Education": ["Growth & Creativity"],
    "Makerspace": ["Growth & Creativity"],
    "AI": ["Growth & Creativity"],
    "Data Science": ["Growth & Creativity"],
    "Cybersecurity": ["Growth & Creativity"],
    "Cloud & Platform": ["Growth & Creativity"],
    "DevOps": ["Growth & Creativity"],
    "Software Development": ["Growth & Creativity"],
    "Web Development": ["Growth & Creativity"],
    "JavaScript": ["Growth & Creativity"],
    "Python": ["Growth & Creativity"],
    "Ruby": ["Growth & Creativity"],
    "Product": ["Growth & Creativity"],
    "UX": ["Growth & Creativity"],
    "Game Development": ["Growth & Creativity"],
    "Technical Writing": ["Growth & Creativity"],
    "Open Source": ["Growth & Creativity"],
    "Robotics": ["Growth & Creativity"],
    "Purpose & Service": ["Purpose & Service"],
    "Politics": ["Purpose & Service"],
    "Faith & Spirituality": ["Purpose & Service"],
    "Civic Tech": ["Purpose & Service"],
    "Policy": ["Purpose & Service"],
    "Crypto & Web3": ["Safety & Stability"],
}

_MASLOW_DEFAULT = "Belonging & Culture"

_SECTOR_SPLIT_BY_TAG = {
    "Economic Development": ["Economics"],
    "Business": ["Entrepreneurship"],
    "Startup": ["Entrepreneurship"],
    "Career Growth": ["Entrepreneurship"],
    "Professional Networking": ["Entrepreneurship"],
}


def _append_sector_split_tags(source: dict) -> None:
    tags = list(source.get("tags") or [])
    seen = set(tags)
    expanded_tags = []
    for tag in tags:
        for mapped in _SECTOR_SPLIT_BY_TAG.get(tag, []):
            if mapped in seen:
                continue
            seen.add(mapped)
            expanded_tags.append(mapped)
    if expanded_tags:
        source["tags"] = tags + expanded_tags


def _append_maslow_tags(source: dict) -> None:
    tags = list(source.get("tags") or [])
    seen = set(tags)
    maslow_tags = []
    for tag in tags:
        for mapped in _MASLOW_BY_TAG.get(tag, []):
            if mapped in seen:
                continue
            seen.add(mapped)
            maslow_tags.append(mapped)
    if not maslow_tags and _MASLOW_DEFAULT not in seen:
        maslow_tags.append(_MASLOW_DEFAULT)
    if maslow_tags:
        source["tags"] = tags + maslow_tags


for _source in sources:
    _append_sector_split_tags(_source)
    _append_maslow_tags(_source)
