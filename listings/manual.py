"""Hand-entered listings from the manual/ folder.

Each *.json file there holds one venue's showings in the listings.json schema,
with a few conveniences for typing by hand:

    {
      "venue": "The Slaughtered Lamb",
      "venue_slug": "slaughtered-lamb",          # optional; matches a scraper's slug if there is one
      "category": "music",                       # default for every showing below
      "showings": [
        {"title": "Dan Pye", "start": "2026-11-14T19:30", "doors": "19:00",
         "price": "£10", "booking_url": "https://..."}
      ]
    }

- `start` may omit the offset ("2026-11-14T19:30"); it's taken as London time.
- `doors` may be a full datetime or just "19:00" (same day as start).
- `id`, `venue`, `category`, `lineup`, `tags`... are filled in if missing.
- Showings whose start has passed are ignored, so a file can be left in place
  and topped up each month.
Files whose names start with "_", contain "example", or don't end in .json are ignored.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from listings.model import LONDON, london_iso, upgrade_showing, validate_listings

DEFAULT_DIR = Path(__file__).resolve().parent.parent / "manual"


@dataclass
class ManualVenue:
    slug: str
    name: str
    file: str
    showings: list[dict] = field(default_factory=list)
    skipped_past: int = 0


def load_manual(directory: Path = DEFAULT_DIR, known_venues: dict | None = None,
                now: datetime | None = None) -> tuple[list[ManualVenue], list[str]]:
    """Load every manual file. Returns (venues, errors). A bad file is reported
    and skipped; it never stops the run."""
    known_venues = known_venues or {}
    now = now or datetime.now(LONDON)
    venues, errors = [], []
    if not directory.is_dir():
        return venues, errors
    for path in sorted(directory.glob("*.json")):
        if path.name.startswith("_") or "example" in path.name.lower():
            continue
        try:
            venues.append(_load_file(path, known_venues, now))
        except Exception as e:
            errors.append(f"manual/{path.name}: {type(e).__name__}: {e}")
    return venues, errors


def _load_file(path: Path, known_venues: dict, now: datetime) -> ManualVenue:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("showings"), list):
        raise ValueError('expected an object with a "showings" list')
    name = (data.get("venue") or "").strip()
    slug = (data.get("venue_slug") or _slugify(name)).strip()
    if not slug:
        raise ValueError('needs "venue" (and optionally "venue_slug")')
    if slug in known_venues:
        name = known_venues[slug].name  # use the scraper's spelling so the venue groups together
    if not name:
        raise ValueError('needs "venue"')
    default_category = data.get("category", "film")

    venue = ManualVenue(slug=slug, name=name, file=f"manual/{path.name}")
    for i, raw in enumerate(data["showings"]):
        try:
            showing = _normalise(raw, slug, name, default_category)
        except Exception as e:
            raise ValueError(f"showing #{i + 1} ({raw.get('title', '?')!r}): {e}") from e
        if datetime.fromisoformat(showing["start"]) < now:
            venue.skipped_past += 1
            continue
        venue.showings.append(showing)
    validate_listings({"generated_at": london_iso(now), "showings": venue.showings})
    return venue


def _normalise(raw: dict, slug: str, name: str, default_category: str) -> dict:
    if not raw.get("title") or not raw.get("start"):
        raise ValueError('needs "title" and "start"')
    start = _london(raw["start"])
    doors = raw.get("doors")
    if doors and re.fullmatch(r"\d{1,2}:\d{2}", doors.strip()):
        h, m = map(int, doors.split(":"))
        doors = london_iso(start.replace(hour=h, minute=m))
    elif doors:
        doors = london_iso(_london(doors))
    category = raw.get("category", default_category)
    key = raw.get("id") or hashlib.sha1(f"{raw['title']}|{start.isoformat()}".encode()).hexdigest()[:12]
    showing = {
        **raw,
        "id": key if str(key).startswith(f"{slug}:") else f"{slug}:manual-{key}",
        "venue": name,
        "category": category,
        "title": raw["title"].strip(),
        "start": london_iso(start),
        "doors": doors,
        "lineup": raw.get("lineup", []) if category == "music" else [],
        "tags": list(dict.fromkeys([*raw.get("tags", []), "manual"])),
    }
    return upgrade_showing(showing)


def _london(value: str) -> datetime:
    dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=LONDON)


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
