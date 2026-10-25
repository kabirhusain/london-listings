"""Sadler's Wells (Angel), the main theatre and Lilian Baylis Studio.

Source (checked 2026-10-25): the ticketing site (my.sadlerswells.com,
Tessitura) is behind Imperva Incapsula bot protection, so we don't use it.
The WordPress site lists shows on /whats-on/ and each show page
server-renders its performances:

  div.c-event-instance
    .c-event-instance__date        "Friday 6 November" (no year)
    .c-event-instance__time        "2 pm"
    .c-event-instance__price       "From: £45.00"
    .c-event-instance__venue-name  "Sadler's Wells Theatre" / "Peacock Theatre" / ...
    [data-performance-id]          booking button with data-booking-url

The listing also covers the Peacock Theatre and Sadler's Wells East, which are
separate buildings; only Angel (main theatre + Lilian Baylis Studio) is kept.
"""

from __future__ import annotations

import re
from datetime import datetime

from bs4 import BeautifulSoup

from listings.http import PoliteClient
from listings.model import LONDON, Showing, london_iso
from listings.text import page_description, date_without_year, parse_clock, tidy_title
from listings.venues.base import Venue

SITE = "https://www.sadlerswells.com"
KEEP_VENUES = ("sadler's wells theatre", "lilian baylis studio")
PAGE_MAX_AGE = 12 * 3600


class SadlersWells(Venue):
    slug = "sadlers-wells"
    name = "Sadler's Wells"
    source_description = f"Show pages on {SITE} (ticketing site is bot-protected)"

    def fetch(self, client: PoliteClient) -> list[Showing]:
        listing = BeautifulSoup(client.get(f"{SITE}/whats-on/").text, "html.parser")
        shows = sorted({a["href"] for a in listing.find_all("a", href=True)
                        if re.match(rf"{re.escape(SITE)}/whats-on/[a-z0-9-]+/?$", a["href"])})
        now = datetime.now(LONDON)
        showings = {}
        for url in shows:
            soup = BeautifulSoup(client.get(url, max_age=PAGE_MAX_AGE).text, "html.parser")
            og_title = soup.find("meta", property="og:title")
            title = tidy_title((og_title["content"] if og_title else url.rstrip("/").rsplit("/", 1)[-1]).split(" | ")[0].split(" - Sadler")[0])
            og_image = soup.find("meta", property="og:image")
            for inst in soup.select("div.c-event-instance"):
                venue_el = inst.select_one(".c-event-instance__venue-name")
                venue = venue_el.get_text(" ", strip=True).lower().replace("’", "'") if venue_el else ""
                if not any(v in venue for v in KEEP_VENUES):
                    continue
                d_el, t_el = inst.select_one(".c-event-instance__date"), inst.select_one(".c-event-instance__time")
                if not (d_el and t_el):
                    continue
                d = date_without_year(d_el.get_text(" ", strip=True), now.date())
                t = parse_clock(t_el.get_text(" ", strip=True).replace(" ", ""))
                if d is None or t is None:
                    continue
                start = datetime.combine(d, t, tzinfo=LONDON)
                if start < now:
                    continue
                btn = inst.select_one("[data-performance-id]")
                perf = btn["data-performance-id"] if btn else f"{start:%Y%m%d%H%M}"
                book = inst.select_one("a[data-booking-url]")
                price = inst.select_one(".c-event-instance__price")
                price_m = re.search(r"£\s?(\d+(?:\.\d\d)?)", price.get_text() if price else "")
                tags = []
                if "lilian baylis" in venue:
                    tags.append("venue:Lilian Baylis Studio")
                if inst.select_one(".c-availability-indicator--sold-out, .c-event-instance--sold-out"):
                    tags.append("sold-out")
                showings[perf] = Showing(
                    id=f"{self.slug}:{perf}",
                    venue=self.name,
                    category="dance",
                    title=title,
                    start=london_iso(start),
                    runtime_minutes=None,
                    price=(f"From £{float(price_m.group(1)):g}" if price_m and float(price_m.group(1)) > 0 else None),
                    booking_url=book["data-booking-url"] if book else url,
                    info_url=url,
                    image_url=(og_image["content"] if og_image and "logo" not in og_image["content"].lower() else None),
                    description=page_description(soup),
                    tags=tags,
                )
        if not showings:
            raise ValueError("no performances parsed from Sadler's Wells show pages")
        return sorted(showings.values(), key=lambda s: (s.start, s.title))


VENUE = SadlersWells()
