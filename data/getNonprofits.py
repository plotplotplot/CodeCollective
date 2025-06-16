import requests
import json
import time

API_BASE = "https://projects.propublica.org/nonprofits/api/v2/search.json"
DELAY = 0.02  # seconds between requests
MAX_PAGES = 1000  # safety limit

# Cities in the Baltimore-Columbia-Towson MSA (based on Census definitions)
msa_cities = {
    "Annapolis", "Arbutus", "Baltimore", "Bel Air", "Bel Air North", "Bel Air South",
    "Catonsville", "Columbia", "Dundalk", "Edgewood", "Elkridge", "Ellicott City",
    "Essex", "Glen Burnie", "Lansdowne", "Lochearn", "Middle River", "Milford Mill",
    "Owings Mills", "Parkville", "Pikesville", "Randallstown", "Reisterstown",
    "Rosedale", "Severn", "Severna Park", "Towson", "Westminster", "Woodlawn",
    "Aberdeen", "Havre de Grace", "Cockeysville", "Laurel", "Pasadena", "Joppatowne",
    "Perry Hall", "Brooklyn Park", "Ferndale", "Carney", "Jarrettsville", "Fallston",
    "Kingsville", "Sykesville", "Elkton", "Edgewater", "Shady Side", "Churchton",
    "Gambrills", "Crofton", "Deale", "Linthicum", "Jessup", "Savage", "North East"
}

def fetch_page(query, page=0):
    params = {"q": query, "page": page}
    response = requests.get(API_BASE, params=params)
    response.raise_for_status()
    return response.json()

def main():
    page = 0
    all_results = []

    while page < MAX_PAGES:
        print(f"Fetching page {page + 1}...")
        data = fetch_page("Baltimore", page)
        results = data.get("organizations", [])
        if not results:
            print("No more results.")
            break

        for org in results:
            city = str(org.get("city", "")).strip().title()
            if city in msa_cities:
                all_results.append(org)

        page += 1
        time.sleep(DELAY)

    print(f"Total nonprofits in Baltimore MSA: {len(all_results)}")

    with open("baltimore_msa_nonprofits.json", "w") as f:
        json.dump(all_results, f, indent=2)

    print("Saved to baltimore_msa_nonprofits.json")

if __name__ == "__main__":
    main()
