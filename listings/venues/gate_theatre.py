"""Gate Theatre.

Source (checked 2026-10-25): Spektrix ticketing API (https://tickets.gatetheatre.co.uk/gate).
Nothing on sale on 2026-10-24 (between seasons).
"""

from listings.sources.spektrix import SpektrixVenue


class GateTheatre(SpektrixVenue):
    slug = "gate-theatre"
    name = "Gate Theatre"
    api_base = "https://tickets.gatetheatre.co.uk/gate"
    info_page = "https://www.gatetheatre.co.uk/whats-on/"
    default_category = 'theatre'
    rules = ()
    allow_empty = True


VENUE = GateTheatre()
