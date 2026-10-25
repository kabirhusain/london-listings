"""Listings from schema.org Event JSON-LD embedded in a page.

Works for any page that marks up its events, e.g. DICE venue pages
(dice.fm/venue/<slug>: a Place with an "event" list, next ~30 events) and
Songkick venue pages (MusicEvent items with performers).
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime

from listings.http import PoliteClient
from listings.model import LONDON, Showing, london_iso
from listings.text import guess_lineup, tidy_title
from listings.venues.base import Venue


def extract_events(html: str) -> list[dict]:
    """Every schema.org *Event object in the page's JSON-LD blocks."""
    found = []

    def walk(node):
        if isinstance(node, list):
            for n in node:
                walk(n)
        elif isinstance(node, dict):
            types = node.get("@type", [])
            types = types if isinstance(types, list) else [types]
            if any(str(t).endswith("Event") for t in types) and node.get("startDate"):
                found.append(node)
            for key in ("@graph", "event", "events", "subEvent", "itemListElement", "item"):
                if key in node:
                    walk(node[key])

    for block in re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S | re.I):
        try:
            walk(json.loads(block))
        except json.JSONDecodeError:
            continue
    return found


class JsonLdEventsVenue(Venue):
    """Subclasses set slug, name, page_url and optionally category / genre / venue_name_match."""

    page_url: str
    category: str = "music"
    genre: str | None = None
    #: Only keep events whose location name contains this (case-insensitive), if set.
    venue_name_match: str | None = None
    #: Set (e.g. to "@ Folklore") to strip Songkick's trailing " @ <venue>" from names.
    title_suffix: str | None = None
    #: Follow ?page=2, 3... up to this many pages (Songkick paginates; DICE doesn't).
    max_pages: int = 1

    @property
    def source_description(self) -> str:
        return f"schema.org Event JSON-LD on {self.page_url}"

    def _events(self, client: PoliteClient) -> list[dict]:
        events, seen = [], set()
        for n in range(1, self.max_pages + 1):
            url = self.page_url if n == 1 else f"{self.page_url}?page={n}"
            page = [e for e in extract_events(client.get(url).text) if (e.get("url"), e.get("startDate")) not in seen]
            if not page:
                break
            seen |= {(e.get("url"), e.get("startDate")) for e in page}
            events += page
        return events

    def fetch(self, client: PoliteClient) -> list[Showing]:
        now = datetime.now(LONDON)
        showings: dict[str, Showing] = {}
        for ev in self._events(client):
            location = ev.get("location") or {}
            loc_name = location.get("name", "") if isinstance(location, dict) else ""
            if self.venue_name_match and self.venue_name_match.lower() not in loc_name.lower():
                continue
            start = _parse_dt(ev["startDate"])
            if start is None or start < now:
                continue
            title = tidy_title(ev.get("name", ""))
            if self.title_suffix:
                # Songkick names events "<Artist> @ <Venue>", spelling the venue its own way.
                title = re.sub(r"\s+@\s+[^@]+$", "", title).strip() or title
            performers = ev.get("performer") or []
            performers = performers if isinstance(performers, list) else [performers]
            lineup = [p["name"] for p in performers if isinstance(p, dict) and p.get("name")]
            if self.category == "music" and not lineup:
                lineup = guess_lineup(title)
            image = ev.get("image")
            image = image[0] if isinstance(image, list) and image else image if isinstance(image, str) else None
            doors = _parse_dt(ev["doorTime"]) if ev.get("doorTime") else None
            url = ev.get("url") or self.page_url
            key = re.sub(r"\W+", "", url.split("?")[0].rstrip("/").rsplit("/", 1)[-1])[-40:] or \
                hashlib.sha1(f"{title}|{start}".encode()).hexdigest()[:12]
            showing = Showing(
                id=f"{self.slug}:{key}:{start.strftime('%Y%m%dT%H%M')}",
                venue=self.name,
                category=self.category,
                title=title,
                start=london_iso(start),
                doors=london_iso(doors) if doors and doors <= start else None,
                runtime_minutes=None,
                lineup=lineup if self.category == "music" else [],
                genre=self.genre,
                price=_price(ev.get("offers")),
                booking_url=url.split("?utm_")[0],
                image_url=image,
                tags=["sold-out"] if "SoldOut" in json.dumps(ev.get("offers") or {}) else [],
                description=ev.get("description") if isinstance(ev.get("description"), str) else None,
            )
            showings[showing.id] = showing
        if not showings:
            raise ValueError(f"no upcoming events in JSON-LD on {self.page_url}")
        return sorted(showings.values(), key=lambda s: (s.start, s.title))


def _parse_dt(s: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if len(s) <= 10:  # date only: no time, can't place it
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=LONDON)


def _price(offers) -> str | None:
    offers = offers if isinstance(offers, list) else [offers] if offers else []
    prices = []
    for o in offers:
        for key in ("lowPrice", "price"):
            try:
                prices.append(float(o[key]))
                break
            except (KeyError, TypeError, ValueError):
                continue
    if not prices:
        return None
    low = min(prices)
    return "Free" if low == 0 else f"From £{low:.2f}".replace(".00", "")
