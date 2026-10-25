"""Kiln Theatre.

Source (checked 2026-10-25): Spektrix ticketing API (https://tickets.kilntheatre.com/tricycle).
Kiln is a cinema and a theatre; attribute_Type says which.
"""

from listings.sources.spektrix import SpektrixVenue


class KilnTheatre(SpektrixVenue):
    slug = "kiln-theatre"
    name = "Kiln Theatre"
    api_base = "https://tickets.kilntheatre.com/tricycle"
    info_page = "https://kilntheatre.com/whats-on/"
    default_category = None
    rules = (
        ('attribute_Type', r'^Cinema$', 'film'),
        ('attribute_Type', r'^Theatre$', 'theatre'),
    )


VENUE = KilnTheatre()
