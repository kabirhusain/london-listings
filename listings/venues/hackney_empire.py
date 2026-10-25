"""Hackney Empire.

Source (checked 2026-10-25): Spektrix ticketing API
(https://tickets.hackneyempire.co.uk/hackneyempire) for performances. Its
events carry no type attributes, so the category comes from the venue's own
what's-on category pages (/whats-on/category/<theatre|comedy|live-music|opera|
dance|family|podcasts-talks>), matched to Spektrix event names by title.
Unmatched events default to theatre; podcasts/talks are left out.
"""

from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from listings.http import FetchError, PoliteClient
from listings.sources.spektrix import SpektrixVenue
from listings.text import match_key

SITE = "https://www.hackneyempire.co.uk"
# Website category -> our category, in priority order (a show can be in several).
CATEGORY_PAGES = [
    ("comedy", "comedy"),
    ("live-music", "music"),
    ("dance", "dance"),
    ("opera", "theatre"),
    ("theatre", "theatre"),
    ("family", "theatre"),
    ("podcasts-talks", None),
]
MAX_PAGES_PER_CATEGORY = 5


class HackneyEmpire(SpektrixVenue):
    slug = "hackney-empire"
    name = "Hackney Empire"
    api_base = "https://tickets.hackneyempire.co.uk/hackneyempire"
    default_category = "theatre"

    def __init__(self):
        self._site_categories: dict[str, str | None] = {}

    def fetch(self, client: PoliteClient):
        self._site_categories = self._load_site_categories(client)
        return super().fetch(client)

    def category(self, event, instance):
        if super().category(event, instance) is None:  # shared non-show filter
            return None
        key = match_key(event["name"])
        if key in self._site_categories:
            return self._site_categories[key]
        # Names differ slightly between Spektrix and the website
        # ("Lenny Henry" vs "Lenny Henry: Still at Large").
        for site_key, category in self._site_categories.items():
            if key and (key in site_key or site_key in key):
                return category
        words = set(key.split())
        for site_key, category in self._site_categories.items():
            if len(words & set(site_key.split())) >= 3:
                return category
        return self.default_category

    def _load_site_categories(self, client: PoliteClient) -> dict[str, str | None]:
        found: dict[str, str | None] = {}
        for slug, category in CATEGORY_PAGES:
            url = f"{SITE}/whats-on/category/{slug}"
            for _ in range(MAX_PAGES_PER_CATEGORY):
                try:
                    soup = BeautifulSoup(client.get(url).text, "html.parser")
                except FetchError:
                    break
                for title in _event_titles(soup):
                    found.setdefault(match_key(title), category)  # first (highest-priority) category wins
                nxt = soup.find("a", string=re.compile(r"^\s*Next\.?\s*$"))
                if not nxt or not nxt.get("href"):
                    break
                url = urljoin(url, nxt["href"])
        return found


def _event_titles(soup: BeautifulSoup) -> list[str]:
    """Titles from a category page: each event card has an h3.c-media__title."""
    return [h.get_text(" ", strip=True) for h in soup.select("h3.c-media__title") if h.get_text(strip=True)]


VENUE = HackneyEmpire()
