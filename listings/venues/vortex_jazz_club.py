"""Vortex Jazz Club (Dalston).

Source (checked 2026-10-24): WordPress with The Events Calendar, but its REST
API is switched off (404). The iCal export (/events/?ical=1) works. Its
DTSTART is the doors time; the description says "Doors 7:45 PM, Music 8:30 PM"
and usually has a "Line-up:" block of "Name - instrument" lines.
Tickets are sold via Universe.
"""

import re
from datetime import datetime

from listings.model import LONDON, london_iso
from listings.sources.tribe_events import TribeEventsVenue

_MUSIC_TIME = re.compile(r"Music\s+(\d{1,2})[:.](\d{2})\s*(AM|PM)", re.I)
_LINEUP_BLOCK = re.compile(r"Line-?up:?\s*(.*?)(?:\n\s*About\b|\Z)", re.I | re.S)


class VortexJazzClub(TribeEventsVenue):
    slug = "vortex-jazz-club"
    name = "Vortex Jazz Club"
    site = "https://www.vortexjazz.co.uk"
    use_rest = False
    ical_url = "https://www.vortexjazz.co.uk/events/?ical=1"

    def category(self, event):
        return "music"

    def details(self, event, category):
        doors = event["start"].astimezone(LONDON)
        start = doors
        m = _MUSIC_TIME.search(event["description"])
        if m:
            hour = int(m.group(1)) % 12 + (12 if m.group(3).upper() == "PM" else 0)
            music = doors.replace(hour=hour, minute=int(m.group(2)))
            if doors <= music <= doors.replace(hour=23, minute=59):
                start = music
        return {
            "start": start,
            "doors": london_iso(doors) if start != doors else None,
            "lineup": _lineup(event["description"]),
            "genre": "Jazz",
            "description": event["description"].split("About:", 1)[-1] if "About" in event["description"] else event["description"],
        }


def _lineup(description: str) -> list[str]:
    block = _LINEUP_BLOCK.search(description)
    if not block:
        return []
    names = []
    for part in re.split(r"\n|\s/\s(?=[A-Z][^/\n]*\s[-–]\s)", block.group(1)):
        name = re.split(r"\s+[-–]\s+", part)[0].strip(" :\xa0")
        if name and len(name) < 50 and not re.search(r"\bTBC\b|house band", name, re.I):
            names.append(name)
    return names


VENUE = VortexJazzClub()
