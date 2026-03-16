from pathlib import Path
import re


DEFAULT_TEMPLATE_FILE = "eventsmap.html"
DEFAULT_CITY_SENTINEL = "baltimore"


def load_events_map_template(template_path=None):
    template_file = Path(template_path or DEFAULT_TEMPLATE_FILE)
    return template_file.read_text(encoding="utf-8")


def apply_default_city(html_content, city):
    default_city = city or DEFAULT_CITY_SENTINEL
    return re.sub(
        r"const DEFAULT_CITY = '.*?';",
        f"const DEFAULT_CITY = '{default_city}';",
        html_content,
        count=1,
    )


def generate_events_map_page(city, output_filename=None, template_path=None):
    """Create a standalone HTML page that visualizes upcoming events on a map."""
    if not output_filename:
        output_filename = "eventsmap.html" if city == DEFAULT_CITY_SENTINEL else f"eventsmap_{city}.html"

    html_content = load_events_map_template(template_path=template_path)
    html_content = apply_default_city(html_content, city)

    Path(output_filename).write_text(html_content, encoding="utf-8")
    print(f"Events map saved to {output_filename}")
