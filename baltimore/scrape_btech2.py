import requests
import json

url = "https://ecobot.ecomap.dev/api/events?id=257"

response = requests.get(url)
response.raise_for_status()

events = response.json()

print(f"✅ Retrieved {len(events)} events from EcoMap")
print(json.dumps(events[:5], indent=4))  # show first 5

# Optional: save all
with open("baltimore_events.json", "w") as f:
    json.dump(events, f, indent=4)
    print("Saved to baltimore_events.json")
