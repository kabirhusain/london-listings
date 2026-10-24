"""Venue registry.

Each module in this package (other than base) defines one Venue subclass and
exposes an instance as VENUE. Adding a venue means adding one file here.
"""

from __future__ import annotations

import importlib
import pkgutil

from listings.venues.base import Venue


def all_venues() -> dict[str, Venue]:
    venues: dict[str, Venue] = {}
    for info in pkgutil.iter_modules(__path__):
        if info.name.startswith("_") or info.name == "base":
            continue
        module = importlib.import_module(f"{__name__}.{info.name}")
        venue = getattr(module, "VENUE", None)
        if not isinstance(venue, Venue):
            raise TypeError(f"listings.venues.{info.name} must define VENUE = <Venue instance>")
        if venue.slug in venues:
            raise ValueError(f"duplicate venue slug {venue.slug!r}")
        venues[venue.slug] = venue
    return venues
