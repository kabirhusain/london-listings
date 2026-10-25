"""Unicorn Theatre.

Source (checked 2026-10-25): Spektrix ticketing API (https://tickets.unicorntheatre.com/unicorntheatre).
Theatre for children and young audiences.
"""

from listings.sources.spektrix import SpektrixVenue


class UnicornTheatre(SpektrixVenue):
    slug = "unicorn-theatre"
    name = "Unicorn Theatre"
    api_base = "https://tickets.unicorntheatre.com/unicorntheatre"
    info_page = "https://www.unicorntheatre.com/whats-on"
    default_category = 'theatre'
    rules = ()


VENUE = UnicornTheatre()
