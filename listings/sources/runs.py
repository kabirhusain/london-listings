"""Helpers for "run" entries: a production with first/last dates but no
performance times (kind="run", start = first date at 00:00, end = last date)."""

from __future__ import annotations

import re
from datetime import date, datetime

from listings.model import LONDON, Showing, london_iso


def run_showing(venue_slug: str, venue_name: str, *, title: str, first: date, last: date,
                url: str, category: str = "theatre", image_url: str | None = None,
                tags: list[str] | None = None) -> Showing:
    key = re.sub(r"[^a-z0-9]+", "-", url.rstrip("/").rsplit("/", 1)[-1].lower()).strip("-")
    return Showing(
        id=f"{venue_slug}:run:{key}",
        venue=venue_name,
        category=category,
        kind="run",
        title=title,
        start=london_iso(datetime.combine(first, datetime.min.time(), tzinfo=LONDON)),
        end=last.isoformat(),
        runtime_minutes=None,
        booking_url=url,
        image_url=image_url,
        tags=["run", *(tags or [])],
    )
