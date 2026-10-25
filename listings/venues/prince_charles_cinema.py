"""Prince Charles Cinema.

Source choice (checked 2026-10-24):
- No Event JSON-LD (only Yoast's WebPage block). /feed/ is WordPress news, not
  showings. /wp-json/ has no listings namespace. Ticketing is Jack Roe, whose
  booking pages (/prince-charles-cinema/booknow/) robots.txt disallows.
- /whats-on/ server-renders the whole programme (every film and performance,
  months ahead) in one page, so one HTML request covers the venue.

Page structure we rely on (Jack Roe WordPress plugin markup):
  div.jacro-event
    a.liveeventtitle[href]           title and film page
    div.film_img img[src]            poster
    div.running-time span            e.g. "1896", "500mins", "(18)", "Movie Marathons"
    ul.performance-list-items
      div.heading                    "Saturday 24th October" (no year)
      li > a.film_book_button[href]  booknow/<performance id>; a.soldfilm_book_button if sold out
         span.time                   "11:00 pm"
         div.movietag span.tag       e.g. class "tag 35mm", text "35mm"
"""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime, timedelta

from bs4 import BeautifulSoup, Tag

from listings.http import PoliteClient
from listings.model import LONDON, Showing, london_iso
from listings.text import date_without_year
from listings.venues.base import Venue

WHATS_ON_URL = "https://princecharlescinema.com/whats-on/"

_DATE_HEADING = re.compile(r"^(?P<weekday>[A-Za-z]+)\s+(?P<day>\d{1,2})(?:st|nd|rd|th)?\s+(?P<month>[A-Za-z]+)$")
_RUNTIME = re.compile(r"^(\d+)\s*mins?$", re.I)
_BOOKNOW_ID = re.compile(r"/booknow/(\d+)")
# PCC's tag classes -> the names other venues use.
_TAG_NAMES = {"sub": "subtitled", "hoh": "hard-of-hearing", "q-a": "q-and-a"}


class PrinceCharlesCinema(Venue):
    slug = "prince-charles-cinema"
    name = "Prince Charles Cinema"
    source_description = f"Server-rendered programme page ({WHATS_ON_URL})"

    def fetch(self, client: PoliteClient) -> list[Showing]:
        html = client.get(WHATS_ON_URL).text
        showings = parse_whats_on(html, today=datetime.now(LONDON).date())
        if not showings:
            raise ValueError("No showings parsed from the What's On page; the markup may have changed")
        return showings


def parse_whats_on(html: str, today: date) -> list[Showing]:
    soup = BeautifulSoup(html, "html.parser")
    now = datetime.now(LONDON)
    showings: dict[str, Showing] = {}
    for event in soup.select("div.jacro-event"):
        title_link = event.select_one("a.liveeventtitle")
        if title_link is None:
            continue
        title = title_link.get_text(strip=True)
        film_url = title_link.get("href")
        img = event.select_one("div.film_img img")
        image_url = img.get("src") if img else None
        blurb_el = event.select_one("div.jacro-formatted-text")
        description = str(blurb_el) if blurb_el else None
        if image_url and "jacro-plugin/images/default" in image_url:
            image_url = None
        runtime = None
        for span in event.select("div.running-time span"):
            m = _RUNTIME.match(span.get_text(strip=True))
            if m:
                runtime = int(m.group(1))
                break

        for perf_list in event.select("ul.performance-list-items"):
            current_date: date | None = None
            # Headings and performances are siblings in document order.
            for child in perf_list.children:
                if not isinstance(child, Tag):
                    continue
                if "heading" in child.get("class", []):
                    current_date = _parse_heading(child.get_text(strip=True), today)
                elif child.name == "li" and current_date is not None:
                    showing = _parse_performance(child, current_date, title, film_url, image_url, runtime)
                    if showing:
                        showing.description = description
                    if showing and datetime.fromisoformat(showing.start) >= now:
                        showings[showing.id] = showing
    return sorted(showings.values(), key=lambda s: (s.start, s.title))


def _parse_performance(li: Tag, day: date, title, film_url, image_url, runtime) -> Showing | None:
    time_el = li.select_one("span.time")
    if time_el is None:
        return None
    t = datetime.strptime(time_el.get_text(strip=True).upper(), "%I:%M %p").time()
    start = datetime.combine(day, t, tzinfo=LONDON)

    book = li.select_one("a.film_book_button")
    sold_out = li.select_one("a.soldfilm_book_button") is not None
    booking_url = book.get("href") if book is not None else None
    m = _BOOKNOW_ID.search(booking_url or "")
    if m:
        perf_key = m.group(1)
    else:
        perf_key = hashlib.sha1(f"{title}|{start.isoformat()}".encode()).hexdigest()[:12]

    tags = []
    for tag in li.select("div.movietag span.tag"):
        classes = [c for c in tag.get("class", []) if c != "tag"]
        tags.extend(_TAG_NAMES.get(c, c) for c in (classes or [tag.get_text(strip=True).lower()]))
    if sold_out:
        tags.append("sold-out")

    return Showing(
        id=f"prince-charles-cinema:{perf_key}",
        venue=PrinceCharlesCinema.name,
        category="film",
        title=title,
        start=london_iso(start),
        runtime_minutes=runtime,
        booking_url=booking_url or film_url,
        info_url=film_url,
        image_url=image_url,
        tags=list(dict.fromkeys(tags)),
    )


def _parse_heading(text: str, today: date) -> date | None:
    """'Saturday 24th October' -> a date (the heading has no year)."""
    return date_without_year(text, today)


VENUE = PrinceCharlesCinema()
