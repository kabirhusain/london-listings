"""MOTH Club (Hackney).

Source (checked 2026-10-24): mothclub.co.uk renders listings with JavaScript
from DICE's partner API, using a key embedded in the page. We don't reuse
third-party API keys, so we read DICE's public venue page instead, which has
schema.org Event JSON-LD for the next ~30 events. mothclub.co.uk/rss only has
titles and dates. MOTH also hosts comedy and club nights, and the JSON-LD
doesn't say which is which, so everything is filed as music.
"""

from listings.sources.jsonld import JsonLdEventsVenue


class MothClub(JsonLdEventsVenue):
    slug = "moth-club"
    name = "MOTH Club"
    page_url = "https://dice.fm/venue/moth-club-43ox"


VENUE = MothClub()
