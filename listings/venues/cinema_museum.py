"""The Cinema Museum (Kennington).

Source (checked 2026-10-24): WordPress with The Events Calendar; its REST API
(/wp-json/tribe/events/v1/events) has every event with price and image. The
page also has Event JSON-LD and an iCal export. Tickets are sold via Ticketlab.

Nearly everything is a screening (often with a talk or live accompaniment).
Museum tours and walks are left out.
"""

import re

from listings.sources.tribe_events import TribeEventsVenue

_NOT_A_SCREENING = re.compile(r"\btours?\b|\bwalk\b|\bdisco\b|quarterly meeting", re.I)
_LIVE_MUSIC = re.compile(r"live (?:music|accompaniment|score)|\bbioscope\b", re.I)


class CinemaMuseum(TribeEventsVenue):
    slug = "cinema-museum"
    name = "The Cinema Museum"
    site = "https://cinemamuseum.org.uk"

    def category(self, event):
        if "Tours" in event["categories"] or _NOT_A_SCREENING.search(event["title"]):
            return None
        return "film"

    def details(self, event, category):
        tags = [f"series:{c}" for c in event["categories"] if c not in ("Events",)]
        if re.search(r"\b35 ?mm\b", event["title"], re.I):
            tags.append("35mm")
        if _LIVE_MUSIC.search(event["title"] + " " + " ".join(event["categories"]) + " " + event["description"][:600]):
            tags.append("live-music")
        return {"tags": tags}


VENUE = CinemaMuseum()
