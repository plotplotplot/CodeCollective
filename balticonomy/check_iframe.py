import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import sys
import json
import os
import concurrent.futures
from urllib.parse import urlparse

def normalize_url(url):
    if not urlparse(url).scheme:
        return "https://" + url
    return url

def is_iframe_allowed(url):
    url = normalize_url(url)
    try:
        response = requests.head(url, allow_redirects=True, timeout=5)
        headers = response.headers

        xfo = headers.get('X-Frame-Options', '').lower()
        csp = headers.get('Content-Security-Policy', '').lower()

        if 'deny' in xfo or 'sameorigin' in xfo:
            print(f"{url} blocked by X-Frame-Options: {xfo}")
            return False

        if 'frame-ancestors' in csp and not any(origin in csp for origin in ['*', 'self']):
            print(f"{url} blocked by CSP: {csp}")
            return False

        return True
    except Exception as e:
        print(f"Error checking headers for {url}: {e}")
        return False

def screenshot_url(url, filename):
    if os.path.exists(filename):
        print(f"Skipping screenshot (already exists): {filename}")
        return filename

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--window-size=800,800")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")

    driver = webdriver.Remote(
        command_executor='http://localhost:4444/wd/hub',
        options=options
    )

    try:
        print(f"Taking screenshot of: {url}")
        driver.get(url)
        time.sleep(5)
        driver.save_screenshot(filename)
        print(f"Saved screenshot to: {filename}")
    except Exception as e:
        print(f"Failed to screenshot {url}: {e}")
    finally:
        driver.quit()
    return filename

def process_org(org):
    raw_url = org.get("Website")
    if not raw_url:
        return org

    url = normalize_url(raw_url)

    clean_url = url.replace("https://", "").replace("http://", "").replace("/", "_")
    screenshot_path = f"./screenshots/{clean_url}.png"

    if not is_iframe_allowed(url):
        screenshot_url(url, screenshot_path)
        org["screenshot"] = screenshot_path
    else:
        print(f"{url} is iframe-embeddable.")
    return org
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_iframe.py orgs.json")
        sys.exit(1)

    input_file = sys.argv[1]

    with open(input_file, 'r') as f:
        orgs = json.load(f)

    os.makedirs("./screenshots", exist_ok=True)

    def check_org_iframe(org):
        raw_url = org.get("Website")
        if not raw_url:
            return org

        url = normalize_url(raw_url)
        clean_url = url.replace("https://", "").replace("http://", "").replace("/", "_")
        screenshot_path = f"./screenshots/{clean_url}.png"

        if not is_iframe_allowed(url):
            org["needs_screenshot"] = True
            org["normalized_url"] = url
            org["screenshot_path"] = screenshot_path
        else:
            print(f"{url} is iframe-embeddable.")
        return org

    # Phase 1: Check iframe support in parallel
    for orgtype, orglist in orgs.items():
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            orgs[orgtype] = list(executor.map(check_org_iframe, orglist))

    # Phase 2: Screenshot serially
    for orgtype, orglist in orgs.items():
        for org in orglist:
            if org.get("needs_screenshot"):
                url = org["normalized_url"]
                path = org["screenshot_path"]
                screenshot_url(url, path)
                org["screenshot"] = path
                # Clean up helper fields
                del org["needs_screenshot"]
                del org["normalized_url"]
                del org["screenshot_path"]

    with open("orgs_iframe.json", 'w') as f:
        json.dump(orgs, f, indent=2)

