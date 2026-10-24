"""St Pancras Old Church.

Source (checked 2026-10-24): the church has no listings site of its own; gigs
are sold on DICE. DICE's public venue page has schema.org Event JSON-LD for the
next ~25-30 events.
"""

from listings.sources.jsonld import JsonLdEventsVenue


class StPancrasOldChurch(JsonLdEventsVenue):
    slug = "st-pancras-old-church"
    name = "St Pancras Old Church"
    page_url = "https://dice.fm/venue/st-pancras-old-church-dklo"


VENUE = StPancrasOldChurch()
