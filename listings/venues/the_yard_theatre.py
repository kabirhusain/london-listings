"""The Yard Theatre.

Source (checked 2026-10-25): Spektrix ticketing API (https://tickets.theyardtheatre.co.uk/theyard).
Includes Live Drafts (work-in-progress readings).
"""

from listings.sources.spektrix import SpektrixVenue


class TheYardTheatre(SpektrixVenue):
    slug = "the-yard-theatre"
    name = "The Yard Theatre"
    api_base = "https://tickets.theyardtheatre.co.uk/theyard"
    info_page = "https://theyardtheatre.co.uk/whats-on/"
    default_category = 'theatre'
    rules = ()


VENUE = TheYardTheatre()
