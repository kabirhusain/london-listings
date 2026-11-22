"""The Lexington (Pentonville Road).

Source: hand-built PHP site, no JSON-LD or feeds; tickets via See Tickets, DICE,
Ticketmaster, WeGotTickets etc. /events.php server-renders a card per event.

Redesigned around 2026-11-18 (checked 2026-11-22); the old div.grid-item cards
with "Sat October 24, 19:30" dates are gone. Each event is now:

  article.event-card
    a.event-img[href=./event.php?id=<id>]
      span.event-label            "Gig" | "Club" (class "club") | absent (quiz, free DJ nights)
      img[src=../uploads/<id>.jpg]
    p.event-date                  "Sun 22nd November · 7:30pm" (no year; "7pm" without minutes)
    h2.event-title > a            title
    a.pill-filled[href]           ticket link, when there is one
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from listings.http import PoliteClient
from listings.model import LONDON, Showing, london_iso
from listings.text import date_without_year, guess_lineup, tidy_title
from listings.venues.base import Venue

URL = "https://www.thelexington.co.uk/events.php?type=all"
_WHEN = re.compile(
    r"^(?P<day>\w+\s+\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+)\s*[·•|-]\s*"
    r"(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*(?P<ampm>am|pm)$",
    re.IGNORECASE,
)


def parse_when(text: str, today) -> datetime | None:
    """'Sun 22nd November · 7:30pm' -> an aware datetime in London, or None."""
    m = _WHEN.match(re.sub(r"\s+", " ", text).strip())
    if not m:
        return None
    d = date_without_year(m.group("day"), today)
    if d is None:
        return None
    hour = int(m.group("hour")) % 12 + (12 if m.group("ampm").lower() == "pm" else 0)
    start = datetime.combine(d, datetime.min.time(), tzinfo=LONDON).replace(hour=hour, minute=int(m.group("minute") or 0))
    # A club night listed under Friday at "1am" starts in the small hours of Saturday.
    if hour < 5:
        start += timedelta(days=1)
    return start


class TheLexington(Venue):
    slug = "the-lexington"
    name = "The Lexington"
    source_description = f"Server-rendered listing ({URL})"

    def fetch(self, client: PoliteClient) -> list[Showing]:
        resp = client.get(URL)
        soup = BeautifulSoup(resp.text, "html.parser")
        now = datetime.now(LONDON)
        showings = {}
        for card in soup.select("article.event-card"):
            title_el, date_el = card.select_one(".event-title"), card.select_one(".event-date")
            if not (title_el and date_el):
                continue
            start = parse_when(date_el.get_text(" ", strip=True), now.date())
            if start is None or start < now:
                continue
            label_el = card.select_one(".event-label")
            label = label_el.get_text(strip=True).lower() if label_el else ""
            club = label == "club" or (label_el is not None and "club" in label_el.get("class", []))
            title = tidy_title(title_el.get_text(" ", strip=True))
            more = card.select_one('a[href*="event.php?id="]')
            info_url = urljoin(resp.url, more["href"]) if more else None
            tickets = card.select_one('a.pill-filled[href^="http"]')
            img = card.select_one("img[src]")
            id_match = re.search(r"id=(\d+)", more["href"]) if more else None
            key = id_match.group(1) if id_match else f"{title}|{start:%Y%m%d%H%M}"
            showings[key] = Showing(
                id=f"{self.slug}:{key}",
                venue=self.name,
                category="music",
                title=title,
                start=london_iso(start),
                runtime_minutes=None,
                # Only gigs have performers in the title; club nights, quizzes and DJ nights don't.
                lineup=guess_lineup(re.sub(r"\s+-\s+Day \w+.*$", "", title)) if label == "gig" else [],
                booking_url=tickets["href"].strip() if tickets else info_url,
                info_url=info_url if tickets else None,
                image_url=urljoin(resp.url, img["src"]) if img else None,
                tags=["club-night"] if club else [],
            )
        if not showings:
            raise ValueError("no events parsed from The Lexington's listing")
        return sorted(showings.values(), key=lambda s: (s.start, s.title))


VENUE = TheLexington()
