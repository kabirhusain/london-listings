"""Bush Theatre.

Source (checked 2026-10-25): Spektrix ticketing API (https://tickets.bushtheatre.co.uk/bushtheatre).
Only productions (not supplementary events).
"""

from listings.sources.spektrix import SpektrixVenue


class BushTheatre(SpektrixVenue):
    slug = "bush-theatre"
    name = "Bush Theatre"
    api_base = "https://tickets.bushtheatre.co.uk/bushtheatre"
    default_category = None
    rules = (
        ('attribute_WebsiteCategorisation', r'^Production$', 'theatre'),
    )


VENUE = BushTheatre()
