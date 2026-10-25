"""Arcola Theatre.

Source (checked 2026-10-25): Spektrix ticketing API (https://boxoffice.arcolatheatre.com/arcolatheatre).
Arcola Youth Theatre (AYT) sessions and workshops are left out; event names
carry a year prefix ("2026: ") that is stripped.
"""

import re

from listings.sources.spektrix import SpektrixVenue


class ArcolaTheatre(SpektrixVenue):
    slug = "arcola-theatre"
    name = "Arcola Theatre"
    api_base = "https://boxoffice.arcolatheatre.com/arcolatheatre"
    default_category = None
    rules = (
        ('name', r'\bAYT\b', None),
        ('attribute_Genre', r'^Theatre$', 'theatre'),
    )

    def fetch(self, client):
        showings = super().fetch(client)
        for s in showings:  # "2026: The Master Builder" -> "The Master Builder"
            s.title = re.sub(r"^20\d\d:\s*", "", s.title)
            s.match_key = ""
        return showings


VENUE = ArcolaTheatre()
