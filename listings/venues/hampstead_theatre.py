"""Hampstead Theatre.

Source (checked 2026-10-25): the ticketing site (my.hampsteadtheatre.com,
Tessitura) is behind Imperva Incapsula bot protection, so we don't use it.
The theatre's own WordPress site lists productions on /whats-on/ (with a
json-data script of production slugs and dates), and each production page
server-renders every performance:

  li.instances-list__item[data-instances-day="2026-10-30"]
    li.instances-list__time-slot__wrapper[data-time="19:45"][data-preview][data-access]
      a[href="https://my.hampsteadtheatre.com/<production>/<performance>"]

One request for the list plus one per production (about 5-10), cached 12 hours.
"""

from __future__ import annotations

import json
import re
from datetime import datetime

from bs4 import BeautifulSoup

from listings.http import PoliteClient
from listings.model import LONDON, Showing, london_iso
from listings.text import page_description, tidy_title
from listings.venues.base import Venue

SITE = "https://www.hampsteadtheatre.com"
PAGE_MAX_AGE = 12 * 3600


class HampsteadTheatre(Venue):
    slug = "hampstead-theatre"
    name = "Hampstead Theatre"
    source_description = f"Production pages on {SITE} (ticketing site is bot-protected)"

    def fetch(self, client: PoliteClient) -> list[Showing]:
        listing = client.get(f"{SITE}/whats-on/").text
        now = datetime.now(LONDON)
        slugs = []
        m = re.search(r'<script[^>]*id="json-data"[^>]*>(.*?)</script>', listing, re.S)
        if m:
            for item in json.loads(m.group(1)):
                if item.get("post_type") == "production" and any(d >= now.date().isoformat() for d in item.get("dates", [])):
                    slugs.append(item["id"])
        if not slugs:  # fall back to production links on the page
            slugs = sorted(set(re.findall(r"/production/([a-z0-9-]+)/", listing)))
        showings = {}
        for slug in slugs:
            url = f"{SITE}/production/{slug}/"
            soup = BeautifulSoup(client.get(url, max_age=PAGE_MAX_AGE).text, "html.parser")
            og_title = soup.find("meta", property="og:title")
            title = tidy_title((og_title["content"] if og_title else slug.replace("-", " ").title()).split(" - ")[0].split(" | ")[0])
            og_image = soup.find("meta", property="og:image")
            for day in soup.select("li.instances-list__item[data-instances-day]"):
                for slot in day.select("[data-time]"):
                    start = datetime.strptime(f"{day['data-instances-day']} {slot['data-time']}", "%Y-%m-%d %H:%M").replace(tzinfo=LONDON)
                    if start < now:
                        continue
                    link = slot.find("a", href=re.compile(r"my\.hampsteadtheatre\.com/\d+/\d+"))
                    perf = re.search(r"/(\d+)/(\d+)", link["href"]).group(2) if link else f"{slug}-{start:%Y%m%d%H%M}"
                    tags = [t.get_text(strip=True).lower().replace(" ", "-") for t in slot.select(".taxonomy-list__item")]
                    tags += [a for a in (slot.get("data-access") or "").split() if a]
                    if slot.select_one('[data-booking-status="sold-out"]:not([disabled])'):
                        tags.append("sold-out")
                    showings[perf] = Showing(
                        id=f"{self.slug}:{perf}",
                        venue=self.name,
                        category="theatre",
                        title=title,
                        start=london_iso(start),
                        runtime_minutes=None,
                        booking_url=link["href"] if link else url,
                        info_url=url,
                        image_url=og_image["content"] if og_image else None,
                        description=page_description(soup),
                        tags=list(dict.fromkeys(tags)),
                    )
        if not showings:
            raise ValueError("no performances parsed from Hampstead Theatre production pages")
        return sorted(showings.values(), key=lambda s: (s.start, s.title))


VENUE = HampsteadTheatre()
