"""Folklore (Hoxton).

Source (checked 2026-10-24): folklorehoxton.co.uk/whats-on embeds a DICE
widget (needs the widget's API key, which we don't reuse) and there's no DICE
venue page. Songkick's venue calendar (/calendar) has MusicEvent JSON-LD with performers. It's
crowd-sourced, so it may miss shows.
"""

from listings.sources.jsonld import JsonLdEventsVenue


class Folklore(JsonLdEventsVenue):
    slug = "folklore"
    name = "Folklore"
    page_url = "https://www.songkick.com/venues/3597224-folklore/calendar"
    max_pages = 3
    title_suffix = "@ Folklore"


VENUE = Folklore()
