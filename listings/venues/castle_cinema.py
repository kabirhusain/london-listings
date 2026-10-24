"""The Castle Cinema (Homerton).

Source (checked 2026-10-24): own booking system; MovieTheater JSON-LD only, no
event data or feeds. /calendar/ server-renders every film with performance
buttons that carry structured data attributes:

  div.programme-tile
    .tile-name h1                               title
    img.film-poster                             poster
    a.performance-button[data-perf-id][data-start-time="2026-10-25T11:15:00"]
        [data-filters="hard-of-hearing,audio-described"]
        span.sold-out (display:none unless sold out)
"""

from __future__ import annotations

from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from listings.http import PoliteClient
from listings.model import LONDON, Showing, london_iso
from listings.text import tidy_title
from listings.venues.base import Venue

SITE = "https://thecastlecinema.com"
URL = SITE + "/calendar/"


class CastleCinema(Venue):
    slug = "castle-cinema"
    name = "The Castle Cinema"
    source_description = f"Server-rendered calendar with data attributes ({URL})"

    def fetch(self, client: PoliteClient) -> list[Showing]:
        soup = BeautifulSoup(client.get(URL).text, "html.parser")
        now = datetime.now(LONDON)
        showings = {}
        for tile in soup.select("div.programme-tile"):
            name_el = tile.select_one(".tile-name h1") or tile.select_one(".tile-name")
            if name_el is None:
                continue
            title = tidy_title(name_el.get_text(" ", strip=True))
            poster = tile.select_one("img.film-poster")
            image = poster.get("src") if poster else None
            if image and "default-poster" in image:
                image = None
            for btn in tile.select("a.performance-button[data-perf-id][data-start-time]"):
                start = datetime.fromisoformat(btn["data-start-time"]).replace(tzinfo=LONDON)
                if start < now:
                    continue
                tags = [f for f in (btn.get("data-filters") or "").split(",") if f]
                sold = btn.select_one(".sold-out")
                if sold is not None and "display:none" not in (sold.get("style") or "").replace(" ", ""):
                    tags.append("sold-out")
                screen = btn.select_one(".screen")
                if screen:
                    tags.append(f"screen:{screen.get_text(strip=True)}")
                perf = btn["data-perf-id"]
                showings[perf] = Showing(
                    id=f"{self.slug}:{perf}",
                    venue=self.name,
                    category="film",
                    title=title,
                    start=london_iso(start),
                    runtime_minutes=None,
                    booking_url=urljoin(SITE, btn.get("href", "")),
                    image_url=urljoin(SITE, image) if image else None,
                    tags=list(dict.fromkeys(tags)),
                )
        if not showings:
            raise ValueError("no performances parsed from the Castle calendar")
        return sorted(showings.values(), key=lambda s: (s.start, s.title))


VENUE = CastleCinema()
