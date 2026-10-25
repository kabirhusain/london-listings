"""The Garden Cinema (Covent Garden).

Source (checked 2026-10-24): no JSON-LD or feeds; its Savoy booking site
doesn't embed the Events JSON that other Savoy cinemas do. The homepage
server-renders every film with all its screenings:

  div.films-list__by-title__film
    .films-list__by-title__film-title a      title (+ span.film-detail__film__rating)
    img.films-list__by-title__film-thumb     poster
    .screening-panel__day
      .screening-panel__date-title           "Thu 05 Nov" (no year)
      .screening-panel                       classes like "q_and_a"
        a.screening[href]                    time; href ends TcsPerformance_<id>...
"""

from __future__ import annotations

import re
from datetime import datetime

from bs4 import BeautifulSoup

from listings.http import PoliteClient
from listings.model import LONDON, Showing, london_iso
from listings.text import date_without_year, tidy_title
from listings.venues.base import Venue

URL = "https://www.thegardencinema.co.uk/"
_PERF_ID = re.compile(r"TcsPerformance_(\d+)")
_PANEL_TAGS = {"q_and_a": "q-and-a", "relaxed": "relaxed", "subtitled": "subtitled", "parent_and_baby": "parent-and-baby",
               "35mm": "35mm", "intro": "intro", "hoh": "hard-of-hearing", "captioned": "captioned"}


class GardenCinema(Venue):
    slug = "garden-cinema"
    name = "The Garden Cinema"
    source_description = f"Server-rendered homepage ({URL})"

    def fetch(self, client: PoliteClient) -> list[Showing]:
        soup = BeautifulSoup(client.get(URL).text, "html.parser")
        today = datetime.now(LONDON).date()
        now = datetime.now(LONDON)
        showings = {}
        for film in soup.select("div.films-list__by-title__film"):
            link = film.select_one(".films-list__by-title__film-title a")
            if link is None:
                continue
            rating = link.select_one(".film-detail__film__rating")
            cert = rating.get_text(strip=True) if rating else None
            if rating:
                rating.extract()
            title = tidy_title(link.get_text(" ", strip=True))
            synopsis = film.select_one(".films-list__by-title__synopsis")
            if synopsis:
                for more in synopsis.find_all("a"):
                    more.extract()  # "Read More"
            description = synopsis.get_text(" ", strip=True) if synopsis else None  # may end "…" (cut off)
            img = film.select_one("img.films-list__by-title__film-thumb")
            image = img.get("src") if img and img.get("src") else None
            for day in film.select(".screening-panel__day"):
                date_el = day.select_one(".screening-panel__date-title")
                d = date_without_year(date_el.get_text(strip=True), today) if date_el else None
                if d is None:
                    continue
                for panel in day.select(".screening-panel"):
                    a = panel.select_one("a.screening")
                    if a is None:
                        continue
                    try:
                        t = datetime.strptime(a.get_text(strip=True), "%H:%M").time()
                    except ValueError:
                        continue
                    start = datetime.combine(d, t, tzinfo=LONDON)
                    if start < now:
                        continue
                    m = _PERF_ID.search(a.get("href", ""))
                    key = m.group(1) if m else f"{title}|{start.isoformat()}"
                    tags = [f"cert:{cert}"] if cert else []
                    tags += [tag for cls, tag in _PANEL_TAGS.items() if cls in panel.get("class", [])]
                    if "sold" in " ".join(panel.get("class", [])).lower():
                        tags.append("sold-out")
                    showings[key] = Showing(
                        id=f"{self.slug}:{key}",
                        venue=self.name,
                        category="film",
                        title=title,
                        start=london_iso(start),
                        runtime_minutes=None,
                        booking_url=a.get("href") or link.get("href"),
                        image_url=image,
                        tags=tags,
                        description=description,
                    )
        if not showings:
            raise ValueError("no screenings parsed from the Garden Cinema homepage")
        return sorted(showings.values(), key=lambda s: (s.start, s.title))


VENUE = GardenCinema()
