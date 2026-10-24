"""Listings from WordPress sites running "The Events Calendar" (Tribe) plugin.

Preferred: its REST API, /wp-json/tribe/events/v1/events (JSON, paginated,
with price and image). Some sites switch that off; they still have the iCal
export, /events/?ical=1 (or /<slug>/?ical=1).
"""

from __future__ import annotations

import html
import re
from datetime import datetime, timezone

from listings.http import PoliteClient
from listings.ical import parse_events
from listings.model import LONDON, Showing, london_iso
from listings.text import tidy_title
from listings.venues.base import Venue

MAX_PAGES = 10


class TribeEventsVenue(Venue):
    """Subclasses set site and either use_rest=True or ical_url, plus the hooks."""

    site: str  # e.g. "https://cinemamuseum.org.uk"
    use_rest: bool = True
    ical_url: str | None = None

    @property
    def source_description(self) -> str:
        if self.use_rest:
            return f"The Events Calendar REST API ({self.site}/wp-json/tribe/events/v1/events)"
        return f"The Events Calendar iCal feed ({self.ical_url})"

    # -- hooks ---------------------------------------------------------------

    def category(self, event: dict) -> str | None:
        """"film", "music" or None to skip. `event` is normalised (see _normalise)."""
        raise NotImplementedError

    def details(self, event: dict, category: str) -> dict:
        return {}

    # -- shared ----------------------------------------------------------------

    def fetch(self, client: PoliteClient) -> list[Showing]:
        events = self._rest_events(client) if self.use_rest else self._ical_events(client)
        now = datetime.now(timezone.utc)
        showings = []
        for ev in events:
            if ev["start"] < now:
                continue
            category = self.category(ev)
            if category is None:
                continue
            fields = {
                "runtime_minutes": None,
                "image_url": ev["image_url"],
                "price": ev["price"],
                "tags": [],
            }
            fields.update(self.details(ev, category))
            start = fields.pop("start", ev["start"])
            showings.append(Showing(
                id=f"{self.slug}:{ev['id']}",
                venue=self.name,
                category=category,
                title=ev["title"],
                start=london_iso(start),
                booking_url=ev["url"],
                **fields,
            ))
        if not showings:
            raise ValueError("no upcoming film or music events")
        return sorted(showings, key=lambda s: (s.start, s.title))

    def _rest_events(self, client: PoliteClient) -> list[dict]:
        today = datetime.now(LONDON).date().isoformat()
        url = f"{self.site}/wp-json/tribe/events/v1/events?per_page=50&start_date={today}"
        out = []
        for _ in range(MAX_PAGES):
            data, _ = client.get_json(url)
            for e in data.get("events", []):
                out.append({
                    "id": str(e["id"]),
                    "title": tidy_title(e["title"]),
                    "start": datetime.fromisoformat(e["utc_start_date"]).replace(tzinfo=timezone.utc),
                    "end": datetime.fromisoformat(e["utc_end_date"]).replace(tzinfo=timezone.utc),
                    "url": e.get("url"),
                    "image_url": (e.get("image") or {}).get("url") if e.get("image") else None,
                    "price": html.unescape(e.get("cost") or "").strip() or None,
                    "categories": [c["name"] for c in e.get("categories", [])],
                    "description": _strip_html(e.get("description") or ""),
                    "raw": e,
                })
            url = data.get("next_rest_url")
            if not url:
                break
        return out

    def _ical_events(self, client: PoliteClient) -> list[dict]:
        # The export stops at ~50 events, so page on by date with tribe-bar-date.
        raw, seen, url = [], set(), self.ical_url
        for _ in range(MAX_PAGES):
            page = [e for e in parse_events(client.get(url).text) if e.get("UID") not in seen]
            if not page:
                break
            raw += page
            seen |= {e.get("UID") for e in page}
            last_day = max(e["DTSTART"] for e in page).date().isoformat()
            url = f"{self.ical_url}&tribe-bar-date={last_day}"
        out = []
        for e in raw:
            out.append({
                "id": e.get("UID", "").split("@")[0] or e["DTSTART"].isoformat(),
                "title": tidy_title(e.get("SUMMARY", "")),
                "start": e["DTSTART"],
                "end": e.get("DTEND"),
                "url": e.get("URL"),
                "image_url": e.get("ATTACH") if (e.get("ATTACH;params") or "").find("image") >= 0 else None,
                "price": None,
                "categories": [c.strip() for c in e.get("CATEGORIES", "").split(",") if c.strip()],
                "description": e.get("DESCRIPTION", ""),
                "raw": e,
            })
        return out


def _strip_html(s: str) -> str:
    s = re.sub(r"<br\s*/?>|</p>|</li>", "\n", s, flags=re.I)
    return html.unescape(re.sub(r"<[^>]+>", "", s))
