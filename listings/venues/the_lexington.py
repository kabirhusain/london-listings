"""The Lexington (Pentonville Road).

Source (checked 2026-10-24): hand-built PHP site, no JSON-LD or feeds; tickets
via See Tickets, DICE, WeGotTickets etc. /events.php server-renders a card per
event:

  div.grid-item (gig) | div.grid-item-club (club night)
    img[src=../uploads/<id>.jpg]
    span.gig-label | span.club-label
    a.ticket-box[href]               ticket link
    div.event-title                  title
    div.event-date                   "Sat October 24, 19:30" (no year)
    a.link-box[href=./event.php?id=<id>]
"""

from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from listings.http import PoliteClient
from listings.model import LONDON, Showing, london_iso
from listings.text import date_without_year, guess_lineup, tidy_title
from listings.venues.base import Venue

URL = "https://www.thelexington.co.uk/events.php?type=all"
_WHEN = re.compile(r"^(\w+)\s+([A-Za-z]+)\s+(\d{1,2}),\s*(\d{1,2}:\d{2})$")


class TheLexington(Venue):
    slug = "the-lexington"
    name = "The Lexington"
    source_description = f"Server-rendered listing ({URL})"

    def fetch(self, client: PoliteClient) -> list[Showing]:
        resp = client.get(URL)
        soup = BeautifulSoup(resp.text, "html.parser")
        now = datetime.now(LONDON)
        showings = {}
        for card in soup.select("div.grid-item, div.grid-item-club"):
            title_el, date_el = card.select_one(".event-title"), card.select_one(".event-date")
            if not (title_el and date_el):
                continue
            m = _WHEN.match(date_el.get_text(" ", strip=True))
            if not m:
                continue
            weekday, month, day, hhmm = m.groups()
            d = date_without_year(f"{weekday} {day} {month}", now.date())
            if d is None:
                continue
            start = datetime.combine(d, datetime.strptime(hhmm, "%H:%M").time(), tzinfo=LONDON)
            if start < now:
                continue
            club = "grid-item-club" in card.get("class", [])
            title = tidy_title(title_el.get_text(" ", strip=True))
            more = card.select_one("a.link-box[href]")
            tickets = card.select_one('a.ticket-box[href^="http"]')
            img = card.select_one("img[src]")
            key = re.search(r"id=(\d+)", more["href"]).group(1) if more and "id=" in more["href"] else f"{title}|{start:%Y%m%d%H%M}"
            showings[key] = Showing(
                id=f"{self.slug}:{key}",
                venue=self.name,
                category="music",
                title=title,
                start=london_iso(start),
                runtime_minutes=None,
                lineup=[] if club else guess_lineup(re.sub(r"\s+-\s+Day \w+.*$", "", title)),
                booking_url=(tickets["href"].strip() if tickets else urljoin(resp.url, more["href"]) if more else None),
                image_url=urljoin(resp.url, img["src"]) if img else None,
                tags=["club-night"] if club else [],
            )
        if not showings:
            raise ValueError("no events parsed from The Lexington's listing")
        return sorted(showings.values(), key=lambda s: (s.start, s.title))


VENUE = TheLexington()
