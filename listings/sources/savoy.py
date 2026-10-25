"""Listings from Savoy Systems cinema sites (the `<Venue>.dll/WhatsOn` pages).

The What's On page embeds the whole programme as JSON:

    var Events = {"Events": [{"ID", "Title", "RunningTime", "ImageURL",
                               "TypeDescription", "Seasons", "Performances": [
                                   {"ID", "StartDate", "StartTime", "Notes",
                                    "IsSoldOut", "URL", "<flag>": "Y"|"N", ...}]}]}

One request per venue, no HTML parsing.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from urllib.parse import urljoin

from listings.http import PoliteClient
from listings.model import LONDON, Showing, london_iso
from listings.text import tidy_title
from listings.venues.base import Venue

# Per-performance flags whose meaning is clear. Venues define their own codes;
# unknown codes are ignored (the Notes text usually says the same thing).
_FLAG_TAGS = {
    "HoH": "hard-of-hearing",
    "HOH": "hard-of-hearing",
    "SU": "subtitled",
    "QA": "q-and-a",
    "CC": "captioned",
    "AD": "audio-described",
}
_NOTE_TAGS = [
    (re.compile(r"hard of hearing|\bhoh\b", re.I), "hard-of-hearing"),
    (re.compile(r"subtitled", re.I), "subtitled"),
    (re.compile(r"baby|parent", re.I), "parent-and-baby"),
    (re.compile(r"relaxed|autism", re.I), "relaxed"),
    (re.compile(r"q ?& ?a|q and a", re.I), "q-and-a"),
    (re.compile(r"\bintro", re.I), "intro"),
    (re.compile(r"35 ?mm", re.I), "35mm"),
]


def parse_events(html: str) -> list[dict]:
    i = html.find("var Events =")
    if i < 0:
        raise ValueError("no `var Events =` in page; the Savoy page layout has changed")
    start = html.index("{", i)
    data, _ = json.JSONDecoder().raw_decode(html[start:])
    return data["Events"]


class SavoyVenue(Venue):
    """Subclasses set slug, name and whats_on_url."""

    whats_on_url: str

    @property
    def source_description(self) -> str:
        return f"Savoy Systems page with embedded JSON ({self.whats_on_url})"

    def fetch(self, client: PoliteClient) -> list[Showing]:
        resp = client.get(self.whats_on_url)
        now = datetime.now(LONDON)
        showings = []
        for event in parse_events(resp.text):
            event_tags = []
            event_type = (event.get("TypeDescription") or "").strip()
            if event_type and event_type not in ("Film", "Main Feature"):
                event_tags.append(_kebab(event_type))  # e.g. opera, ballet-dance (screenings)
            event_tags += [f"season:{s['SeasonName']}" for s in event.get("Seasons") or [] if s.get("SeasonName")]
            rating = re.search(r"\(([^)]+)\)", event.get("Rating") or "")
            if rating:
                event_tags.append(f"cert:{rating.group(1)}")

            for perf in event.get("Performances", []):
                start = datetime.strptime(f"{perf['StartDate']} {perf['StartTime']}", "%Y-%m-%d %H%M").replace(tzinfo=LONDON)
                if start < now:
                    continue
                tags = list(event_tags)
                tags += [tag for flag, tag in _FLAG_TAGS.items() if perf.get(flag) == "Y"]
                tags += [tag for pattern, tag in _NOTE_TAGS if pattern.search(perf.get("Notes") or "")]
                if perf.get("IsSoldOut") == "Y":
                    tags.append("sold-out")
                showings.append(Showing(
                    id=f"{self.slug}:{perf['ID']}",
                    venue=self.name,
                    category="film",
                    title=tidy_title(event["Title"]),
                    start=london_iso(start),
                    runtime_minutes=event.get("RunningTime") or None,
                    booking_url=urljoin(resp.url, perf["URL"]) if perf.get("URL") else event.get("URL"),
                    image_url=event.get("ImageURL") or None,
                    genre=(event.get("Genre") or None),
                    description=event.get("Synopsis"),
                    tags=list(dict.fromkeys(tags)),
                ))
        if not showings:
            raise ValueError("no upcoming performances in the Savoy Events data")
        return sorted(showings, key=lambda s: (s.start, s.title))


def _kebab(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
