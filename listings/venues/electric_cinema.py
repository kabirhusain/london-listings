"""Electric Cinema (Portobello Road, Notting Hill).

Source (checked 2026-10-24): electriccinema.co.uk renders its programme with
JavaScript from /data/data.json (films + screenings for both Electric
cinemas; Vista behind it). We read that file and keep cinema 603, Portobello.
"""

from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urljoin

from listings.http import PoliteClient
from listings.model import LONDON, Showing, london_iso
from listings.text import tidy_title
from listings.venues.base import Venue

SITE = "https://www.electriccinema.co.uk"
DATA_URL = SITE + "/data/data.json"


class ElectricCinema(Venue):
    slug = "electric-cinema"
    name = "Electric Cinema (Notting Hill)"
    cinema_title = "Portobello"
    source_description = f"Electric Cinema JSON ({DATA_URL})"

    def fetch(self, client: PoliteClient) -> list[Showing]:
        data, _ = client.get_json(DATA_URL)
        cinema_ids = {cid for cid, c in data["cinemas"].items() if c.get("title") == self.cinema_title}
        if not cinema_ids:
            raise ValueError(f"cinema {self.cinema_title!r} not in data.json")
        films = data["films"]
        types = data.get("screeningTypes") or {}
        now = datetime.now(LONDON)
        showings = []
        for s in data["screenings"].values():
            if str(s.get("cinema")) not in cinema_ids:
                continue
            start = datetime.strptime(f"{s['d']} {s['t']}", "%Y-%m-%d %H:%M").replace(tzinfo=LONDON)
            if start < now:
                continue
            film = films.get(str(s["film"]))
            if film is None:
                continue
            tags = []
            if film.get("rating") and film["rating"] != "TBC":
                tags.append(f"cert:{film['rating']}")
            st = s.get("st")
            if st and isinstance(types.get(st), dict) and types[st].get("title"):
                tags.append(types[st]["title"].lower().replace(" ", "-"))
            if s.get("bookable") is False and "closed" not in (s.get("message") or "").lower():
                tags.append("sold-out")
            link = s.get("link") or film.get("link")
            showings.append(Showing(
                id=f"{self.slug}:{s['id']}",
                venue=self.name,
                category="film",
                title=tidy_title(film["title"]),
                start=london_iso(start),
                runtime_minutes=None,
                booking_url=urljoin(SITE, link) if link else SITE,
                image_url=urljoin(SITE, film["image"]) if film.get("image") else None,
                tags=tags,
                description=re.sub(r"^Certificate:[^\n]*\n+", "", film.get("short_synopsis") or ""),
            ))
        if not showings:
            raise ValueError("no upcoming Portobello screenings in data.json")
        return sorted(showings, key=lambda s: (s.start, s.title))


VENUE = ElectricCinema()
