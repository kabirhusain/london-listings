"""Battersea Arts Centre.

Source (checked 2026-10-25): Spektrix ticketing API (https://tickets.bac.org.uk/bac).
Public programme and Grand Hall events; business events and talks are left out.
"""

from listings.sources.spektrix import SpektrixVenue


class BatterseaArtsCentre(SpektrixVenue):
    slug = "battersea-arts-centre"
    name = "Battersea Arts Centre"
    api_base = "https://tickets.bac.org.uk/bac"
    default_category = None
    rules = (
        ('name', r'artist talk|\btalk\b', None),
        ('name', r'pictures|screening', 'film'),
        ('attribute_Workstream', r'Public Programme|Grand Hall', 'theatre'),
    )


VENUE = BatterseaArtsCentre()
