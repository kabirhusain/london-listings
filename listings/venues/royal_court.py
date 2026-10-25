"""Royal Court Theatre.

Source (checked 2026-10-25): Spektrix ticketing API (https://tickets.royalcourttheatre.com/royalcourt).
Events held elsewhere (hotels, bowling alleys, online) are left out.
"""

from listings.sources.spektrix import SpektrixVenue


class RoyalCourt(SpektrixVenue):
    slug = "royal-court"
    name = "Royal Court Theatre"
    api_base = "https://tickets.royalcourttheatre.com/royalcourt"
    info_page = "https://royalcourttheatre.com/whats-on/"
    default_category = 'theatre'
    rules = (
        ('attribute_TicketVenue2', r'^(?!Royal Court).', None),
        ('name', r'screening', None),
    )


VENUE = RoyalCourt()
