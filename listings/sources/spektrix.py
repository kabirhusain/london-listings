"""Listings from a venue's Spektrix ticketing system.

Spektrix exposes a public, read-only JSON API per venue (the venue's own site
calls it from the browser):

    <api_base>/api/v3/events                    every event, with attribute_* fields
    <api_base>/api/v3/instances?startFrom=DATE  every performance from DATE

Two requests cover the whole programme. Venues set up their own attribute_*
fields, so each venue subclass decides which events are film or music.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

from listings.http import PoliteClient
from listings.model import LONDON, Showing, london_iso
from listings.text import tidy_title
from listings.venues.base import Venue

# Spektrix test events that venues forget to hide, e.g. "Test Event - £0.01", "Georgia's Test Screen".
_TEST_EVENT = re.compile(r"\btest\b", re.I)


def fetch_spektrix(client: PoliteClient, api_base: str, start_from: date) -> tuple[dict[str, dict], list[dict]]:
    """Return ({event id: event}, upcoming non-cancelled instances)."""
    events, _ = client.get_json(f"{api_base}/api/v3/events")
    instances, _ = client.get_json(f"{api_base}/api/v3/instances?startFrom={start_from.isoformat()}")
    now = datetime.now(timezone.utc)
    upcoming = [i for i in instances if not i.get("cancelled") and spektrix_utc(i["startUtc"]) >= now]
    return {e["id"]: e for e in events}, upcoming


def spektrix_utc(s: str) -> datetime:
    return datetime.fromisoformat(s.removesuffix("Z")).replace(tzinfo=timezone.utc)


def instance_number(spektrix_id: str) -> str:
    """Spektrix ids look like "3791601AVKCB..."; booking pages use the leading digits."""
    m = re.match(r"\d+", spektrix_id)
    return m.group(0) if m else spektrix_id


def parse_doors(text: str | None, start: datetime) -> str | None:
    """Turn a free-text doors time ("19:00", "7pm", "7:30pm", "5:00") into an ISO
    datetime on the start's date. Returns None unless it's within 3 hours before start."""
    if not text:
        return None
    m = re.search(r"(\d{1,2})(?:[:.](\d{2}))?\s*(am|pm)?", text.strip(), re.I)
    if not m:
        return None
    hour, minute, ampm = int(m.group(1)), int(m.group(2) or 0), (m.group(3) or "").lower()
    if ampm == "pm" and hour < 12:
        hour += 12
    elif not ampm and hour < 12 and start.astimezone(LONDON).hour >= 12:
        hour += 12  # "5:00" before an evening show means 17:00
    if hour > 23 or minute > 59:
        return None
    local_start = start.astimezone(LONDON)
    doors = local_start.replace(hour=hour, minute=minute, second=0)
    if not (local_start - timedelta(hours=3) <= doors <= local_start):
        return None
    return london_iso(doors)


class SpektrixVenue(Venue):
    """A venue whose listings come straight from its Spektrix API."""

    #: e.g. "https://buy.ica.art/ica" (the part before /api/v3).
    api_base: str

    @property
    def source_description(self) -> str:
        return f"Spektrix ticketing API ({self.api_base}/api/v3)"

    # -- hooks for subclasses ------------------------------------------------

    def category(self, event: dict, instance: dict) -> str | None:
        """"film", "music", or None to leave the event out."""
        raise NotImplementedError

    def details(self, event: dict, instance: dict, category: str) -> dict:
        """Extra Showing fields (tags, genre, doors, lineup...). Override as needed."""
        return {}

    def booking_url(self, instance: dict) -> str:
        return f"{self.api_base}/website/ChooseSeats.aspx?EventInstanceId={instance_number(instance['id'])}"

    # -- shared logic -------------------------------------------------------

    def fetch(self, client: PoliteClient) -> list[Showing]:
        events, instances = fetch_spektrix(client, self.api_base, datetime.now(LONDON).date())
        showings = []
        for inst in instances:
            event = events.get(inst["event"]["id"])
            if event is None or _TEST_EVENT.search(event["name"]):
                continue
            category = self.category(event, inst)
            if category is None:
                continue
            start = spektrix_utc(inst["startUtc"])
            fields = {
                "runtime_minutes": (event.get("duration") or None) if category == "film" else None,
                "image_url": event.get("imageUrl") or None,
                "tags": [],
            }
            fields.update(self.details(event, inst, category))
            showings.append(Showing(
                id=f"{self.slug}:{inst['id']}",
                venue=self.name,
                category=category,
                title=tidy_title(event["name"]),
                start=london_iso(start),
                booking_url=self.booking_url(inst),
                **fields,
            ))
        if not showings:
            raise ValueError("Spektrix returned no film or music performances")
        return sorted(showings, key=lambda s: (s.start, s.title))
