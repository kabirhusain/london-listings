"""Union Chapel (Islington).

Source (checked 2026-10-24): no JSON-LD, feeds or JSON endpoint; tickets via
Gigantic and DICE. /whats-on server-renders a card per event:

  div.item[data-chron="2026-10-22 00:00:00"]
    .card-image[style=background-image:url(...)]
    p.card-title                         title
    .card-bottom a.btn-primary[href]     booking link (Gigantic URLs end with the doors time)

Start times are only on each event's page ("Doors 6.30pm ... starts 7.30pm"),
so we fetch those and cache them for a week.

Union Chapel hosts gigs, film-festival tours, talks and comedy without a
machine-readable type; film tours are recognised by name, everything else is
filed as music.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from bs4 import BeautifulSoup

from listings.http import FetchError, PoliteClient
from listings.model import LONDON, Showing, london_iso
from listings.text import find_doors_and_start, guess_lineup, tidy_title
from listings.venues.base import Venue

URL = "https://unionchapel.org.uk/whats-on"
DETAIL_MAX_AGE = 7 * 86400
_NOT_A_SHOW = re.compile(r"guided tour|open house|\btours? of\b", re.I)
_FILM = re.compile(r"film festival|film tour|\bscreening\b|\bcinema\b|\bbanff\b", re.I)
_GIGANTIC_TIME = re.compile(r"/(\d{4}-\d{2}-\d{2})-(\d{2})-(\d{2})$")
# Card titles often end with the date, e.g. "Ocean Film Festival World Tour: 22 OCT".
_TITLE_DATE = re.compile(r"[:\-–]?\s*(?:(?:mon|tue|wed|thu|fri|sat|sun)[a-z]*\s+)?\d{1,2}(?:st|nd|rd|th)?\s+[a-z]{3,9}\.?\s*(?:\d{2,4})?$", re.I)


class UnionChapel(Venue):
    slug = "union-chapel"
    name = "Union Chapel"
    source_description = f"Server-rendered listing ({URL}) + event pages for start times"

    def fetch(self, client: PoliteClient) -> list[Showing]:
        soup = BeautifulSoup(client.get(URL).text, "html.parser")
        now = datetime.now(LONDON)
        showings = {}
        for item in soup.select("div.item[data-chron]"):
            day = datetime.strptime(item["data-chron"][:10], "%Y-%m-%d").date()
            if day < now.date():
                continue
            link = item.select_one("a[href]")
            title_el = item.select_one("p.card-title")
            if not (link and title_el):
                continue
            title = _TITLE_DATE.sub("", tidy_title(title_el.get_text(" ", strip=True))).strip(" :-–|")
            if _NOT_A_SHOW.search(title):
                continue
            book = item.select_one(".card-bottom a.btn-primary")
            booking = (book["href"] if book else link["href"]).strip()

            doors_t = start_t = None
            try:
                page = client.get(link["href"], max_age=DETAIL_MAX_AGE).text
                text = BeautifulSoup(page, "html.parser").get_text(" ", strip=True)
                doors_t, start_t = find_doors_and_start(text)
            except FetchError:
                pass
            g = _GIGANTIC_TIME.search(booking)
            if doors_t is None and g:
                doors_t = datetime.strptime(f"{g.group(2)}:{g.group(3)}", "%H:%M").time()
            tags = []
            if start_t is None:
                if doors_t is None:
                    continue  # no time at all; can't place it
                start_t, doors_t = doors_t, None
                tags.append("time-is-doors")
            start = datetime.combine(day, start_t, tzinfo=LONDON)
            doors = datetime.combine(day, doors_t, tzinfo=LONDON) if doors_t else None
            if doors and not (start - timedelta(hours=3) <= doors <= start):
                doors = None
            if start < now:
                continue
            category = "film" if _FILM.search(title) else "music"
            img = re.search(r"url\((?:&quot;|\"|')?([^)\"'&]+)", str(item.select_one(".card-image") or ""))
            key = link["href"].rstrip("/").rsplit("/", 1)[-1]
            showings[key] = Showing(
                id=f"{self.slug}:{key}",
                venue=self.name,
                category=category,
                title=title,
                start=london_iso(start),
                doors=london_iso(doors) if doors else None,
                runtime_minutes=None,
                lineup=guess_lineup(title) if category == "music" else [],
                booking_url=booking,
                image_url=img.group(1) if img else None,
                tags=tags,
            )
        if not showings:
            raise ValueError("no events parsed from Union Chapel's what's-on page")
        return sorted(showings.values(), key=lambda s: (s.start, s.title))


VENUE = UnionChapel()
