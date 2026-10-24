"""Listings from Clusterflick's open per-venue data.

Clusterflick (https://clusterflick.com) publishes a normalised JSON file for
each of ~480 London venues, rebuilt daily, as GitHub release assets:

    https://github.com/clusterflick/data-transformed/releases/latest/download/<venue-id>

The data is licensed CC BY 4.0 (https://clusterflick.com/data-licence), which
requires the credit in ATTRIBUTION wherever it's shown and a note that we
changed it (we reshape it into our own schema). The `themoviedb` block belongs
to TMDB and isn't covered by that licence, so we don't use it.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from listings.http import PoliteClient
from listings.model import Showing, london_iso
from listings.venues.base import Venue

RELEASE_URL = "https://github.com/clusterflick/data-transformed/releases/latest/download/{venue_id}"
ATTRIBUTION = "Screening data from Clusterflick - clusterflick.com (CC BY 4.0). Modified: reshaped into this schema."
_SEASON_NOTE = re.compile(r"^Part of (?P<season>.+)$")

# Clusterflick flag name -> our tag.
_ACCESSIBILITY_TAGS = {
    "subtitled": "subtitled",
    "audioDescription": "audio-described",
    "hardOfHearing": "hard-of-hearing",
    "relaxed": "relaxed",
    "babies": "parent-and-baby",
}


class ClusterflickVenue(Venue):
    """A venue whose listings come from Clusterflick. Subclasses set the ids."""

    #: Clusterflick's id for the venue, e.g. "bfi.org.uk-southbank".
    clusterflick_id: str
    #: Keep only / drop performances on these screens (case-insensitive), for
    #: venues that share a building, e.g. Bertha DocHouse inside Curzon Bloomsbury.
    only_screens: tuple[str, ...] = ()
    exclude_screens: tuple[str, ...] = ()
    #: Prefix to strip from titles, e.g. "DocHouse: ".
    title_prefix: str | None = None

    def __init__(self):
        self._release: str | None = None

    @property
    def source_description(self) -> str:
        return f"Clusterflick open data ({RELEASE_URL.format(venue_id=self.clusterflick_id)})"

    def fetch(self, client: PoliteClient) -> list[Showing]:
        url = RELEASE_URL.format(venue_id=self.clusterflick_id)
        data, resp = client.get_json(url)
        # The "latest" URL redirects to .../releases/download/<tag>/<venue-id>.
        m = re.search(r"/releases/download/([^/]+)/", " ".join(resp.redirects))
        self._release = m.group(1) if m else None
        if not isinstance(data, list):
            raise ValueError(f"Unexpected Clusterflick payload for {self.clusterflick_id}: {type(data).__name__}")
        only = {x.lower() for x in self.only_screens}
        exclude = {x.lower() for x in self.exclude_screens}
        if only or exclude:
            data = [
                {**film, "performances": [
                    p for p in film.get("performances", [])
                    if (not only or (p.get("screen") or "").lower() in only)
                    and (p.get("screen") or "").lower() not in exclude
                ]}
                for film in data
            ]
        showings = showings_from_clusterflick(
            data, venue_slug=self.slug, venue_name=self.name, clusterflick_id=self.clusterflick_id
        )
        if self.title_prefix:
            for s in showings:
                if s.title.lower().startswith(self.title_prefix.lower()):
                    s.title = s.title[len(self.title_prefix):].strip()
        return showings

    def source_info(self) -> dict:
        return {
            **super().source_info(),
            "release": self._release,
            "attribution": ATTRIBUTION,
        }


def showings_from_clusterflick(
    data: list[dict],
    venue_slug: str,
    venue_name: str,
    clusterflick_id: str,
    now: datetime | None = None,
) -> list[Showing]:
    now = now or datetime.now(timezone.utc)
    showings: dict[str, Showing] = {}
    for film in data:
        overview = film.get("overview") or {}
        duration_ms = overview.get("duration")
        runtime = round(duration_ms / 60000) if duration_ms else None
        # e.g. "bfi.org.uk-southbank-1263A3A8-..." -> "1263A3A8-..." (BFI's article id)
        film_key = film["showingId"].removeprefix(f"{clusterflick_id}-")
        film_tags = []
        if film.get("category"):
            film_tags.append(film["category"])

        for perf in film.get("performances", []):
            start = datetime.fromtimestamp(perf["time"] / 1000, tz=timezone.utc)
            if start < now:
                continue
            start_iso = london_iso(start)
            # Include the screen so two screenings of one film at the same minute
            # couldn't collide (not seen in BFI data so far, but cheap insurance).
            showing_id = f"{venue_slug}:{film_key}:{start.strftime('%Y%m%dT%H%MZ')}"
            if perf.get("screen"):
                showing_id += f":{_kebab(perf['screen'])}"
            showings[showing_id] = Showing(
                id=showing_id,
                venue=venue_name,
                category="film",
                title=film["title"].strip(),
                start=start_iso,
                runtime_minutes=runtime,
                booking_url=perf.get("bookingUrl") or film.get("url"),
                image_url=None,  # Clusterflick doesn't publish venue images
                tags=_dedupe(film_tags + _performance_tags(perf)),
            )
    return sorted(showings.values(), key=lambda s: (s.start, s.title))


def _performance_tags(perf: dict) -> list[str]:
    tags = []
    for flag, on in (perf.get("accessibility") or {}).items():
        if on:
            tags.append(_ACCESSIBILITY_TAGS.get(flag, _kebab(flag)))
    fmt = perf.get("format") or {}
    if fmt.get("source"):
        tags.append(str(fmt["source"]).lower())  # e.g. 35mm, 70mm
    if fmt.get("dimension") == "3d":
        tags.append("3d")
    if (perf.get("status") or {}).get("soldOut"):
        tags.append("sold-out")
    if perf.get("screen"):
        tags.append(f"screen:{perf['screen']}")
    m = _SEASON_NOTE.match((perf.get("notes") or "").strip())
    if m:
        tags.append(f"season:{m.group('season')}")
    return tags


def _kebab(name: str) -> str:
    name = re.sub(r"(?<=[a-z])(?=[A-Z])", "-", name)
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))
