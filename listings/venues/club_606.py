"""606 Club (Chelsea).

Source (checked 2026-10-24): own site, no JSON-LD or feeds. /events/?d=YYYY-MM-DD
server-renders one week:

  div.event-listing
    a.banner                    "Mon 19th Oct - 8:00pm"
    img                         image
    p.h4                        title
    a[href=/events/view/<slug>/]

We read the next WEEKS weeks.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from listings.http import PoliteClient
from listings.model import LONDON, Showing, london_iso
from listings.text import date_without_year, guess_lineup, parse_clock, tidy_title
from listings.venues.base import Venue

SITE = "https://www.606club.co.uk"
WEEKS = 8


class Club606(Venue):
    slug = "606-club"
    name = "606 Club"
    source_description = f"Server-rendered weekly listings ({SITE}/events/?d=...)"

    def fetch(self, client: PoliteClient) -> list[Showing]:
        now = datetime.now(LONDON)
        showings = {}
        for week in range(WEEKS):
            day0 = (now + timedelta(days=7 * week)).date()
            soup = BeautifulSoup(client.get(f"{SITE}/events/?d={day0.isoformat()}").text, "html.parser")
            for card in soup.select("div.event-listing"):
                banner = card.select_one("a.banner")
                title_el = card.select_one("p.h4")
                if not (banner and title_el):
                    continue
                when = banner.get_text(" ", strip=True).replace(" th ", "th ").replace(" st ", "st ").replace(" nd ", "nd ").replace(" rd ", "rd ")
                m = re.match(r"^(.+?)\s*-\s*(\d{1,2}(?::\d{2})?\s*[ap]m)$", re.sub(r"\s+", " ", when), re.I)
                if not m:
                    continue
                d = date_without_year(m.group(1), now.date())
                t = parse_clock(m.group(2))
                if d is None or t is None:
                    continue
                start = datetime.combine(d, t, tzinfo=LONDON)
                if start < now:
                    continue
                title = tidy_title(title_el.get_text(" ", strip=True))
                img = card.select_one("img[src]")
                href = banner.get("href", "")
                key = href.strip("/").rsplit("/", 1)[-1] + f":{start:%Y%m%d}"
                showings[key] = Showing(
                    id=f"{self.slug}:{key}",
                    venue=self.name,
                    category="music",
                    title=title,
                    start=london_iso(start),
                    runtime_minutes=None,
                    lineup=guess_lineup(title),
                    genre="Jazz",
                    booking_url=urljoin(SITE, href),
                    image_url=img["src"] if img else None,
                    tags=[],
                )
        if not showings:
            raise ValueError("no events parsed from the 606 Club listings")
        return sorted(showings.values(), key=lambda s: (s.start, s.title))


VENUE = Club606()
