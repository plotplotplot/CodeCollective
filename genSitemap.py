import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

BASE_URL = "https://codecollective.us"
SITEMAP_FILE = "sitemap.xml"
ROOT_DIR = Path(".")
EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    "audio",
    "css",
    "data",
    "event_images",
    "fonts",
    "images",
    "js",
    "legacy",
    "levatel",
    "m",
    "portal",
    "templates",
}
EXCLUDED_FILES = {
    "geocode_cache.html",
    "meetup_past.html",
    "out.txt",
}


def iter_public_html_files(root_dir: Path):
    for path in root_dir.rglob("*.html"):
        rel_parts = path.relative_to(root_dir).parts
        if any(part in EXCLUDED_DIRS for part in rel_parts):
            continue
        if path.name in EXCLUDED_FILES:
            continue
        yield path


def read_html(path: Path) -> BeautifulSoup:
    with path.open("r", encoding="utf-8") as file:
        return BeautifulSoup(file, "html.parser")


def should_include(path: Path) -> bool:
    soup = read_html(path)

    robots = soup.find("meta", attrs={"name": "robots"})
    if robots and "noindex" in robots.get("content", "").lower():
        return False

    canonical = soup.find("link", attrs={"rel": "canonical"})
    if canonical:
        href = canonical.get("href", "").strip()
        if href:
            parsed = urlparse(href)
            if parsed.netloc and parsed.netloc != "codecollective.us":
                return False

    return True


def path_to_url(base_url: str, path: Path, root_dir: Path) -> str:
    rel_path = path.relative_to(root_dir).as_posix()
    if rel_path == "index.html":
        return f"{base_url}/"
    if path.name == "index.html":
        return f"{base_url}/{path.parent.as_posix()}/"
    return urljoin(f"{base_url}/", rel_path)


def collect_urls(base_url: str, root_dir: Path):
    urls = set()
    for path in iter_public_html_files(root_dir):
        if should_include(path):
            urls.add(path_to_url(base_url, path, root_dir))
    return urls

def generate_sitemap(links, output_file):
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")

    sitemap_header = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
"""

    url_entries = ""
    for link in sorted(links):
        url_entries += f"""  <url>
    <loc>{link}</loc>
    <lastmod>{current_date}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
"""

    sitemap_footer = """</urlset>
"""

    with open(output_file, "w", encoding="utf-8") as file:
        file.write(sitemap_header)
        file.write(url_entries)
        file.write(sitemap_footer)

    print(f"Sitemap generated: {output_file}")

if __name__ == "__main__":
    all_links = collect_urls(BASE_URL, ROOT_DIR)
    if all_links:
        generate_sitemap(all_links, SITEMAP_FILE)
        print(f"Total URLs in sitemap: {len(all_links)}")
    else:
        print("No links found.")
