"""The Old Vic (Waterloo). Run entries: dates per production, no times.

Source (checked 2026-10-25): performance times are only on the ticketing site
(my.oldvictheatre.com, Tessitura), which is behind Imperva Incapsula, so we
don't use it. The theatre's own site lists productions on /productions/ (links
to /stage/<slug>/), and each page has its run in .event-hero-right__dates,
e.g. "10 Nov 2026–09 Jan 2027".
"""

from __future__ import annotations

import re
from datetime import datetime

from bs4 import BeautifulSoup

from listings.http import PoliteClient
from listings.model import LONDON
from listings.sources.runs import run_showing
from listings.text import parse_date_range, tidy_title
from listings.venues.base import Venue

SITE = "https://www.oldvictheatre.com"
PAGE_MAX_AGE = 24 * 3600


class OldVic(Venue):
    slug = "old-vic"
    name = "The Old Vic"
    source_description = f"Production pages on {SITE} (run dates only; ticketing site is bot-protected)"

    def fetch(self, client: PoliteClient):
        listing = BeautifulSoup(client.get(f"{SITE}/productions/").text, "html.parser")
        pages = sorted({a["href"] for a in listing.find_all("a", href=True)
                        if re.match(rf"{re.escape(SITE)}/stage/[a-z0-9-]+/?$", a["href"])})
        today = datetime.now(LONDON).date()
        showings = []
        for url in pages:
            soup = BeautifulSoup(client.get(url, max_age=PAGE_MAX_AGE).text, "html.parser")
            dates_el = soup.select_one(".event-hero-right__dates")
            dates = parse_date_range(dates_el.get_text(" ", strip=True)) if dates_el else None
            if not dates or dates[1] < today:
                continue
            h1 = soup.find("h1")
            title = tidy_title(h1.get_text(" ", strip=True) if h1 else url.rstrip("/").rsplit("/", 1)[-1])
            og_image = soup.find("meta", property="og:image")
            showings.append(run_showing(
                self.slug, self.name, title=title, first=dates[0], last=dates[1], url=url,
                image_url=og_image["content"] if og_image else None,
            ))
        if not showings:
            raise ValueError("no current or upcoming runs parsed from oldvictheatre.com")
        return sorted(showings, key=lambda s: s.start)


VENUE = OldVic()
