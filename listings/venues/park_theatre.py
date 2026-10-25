"""Park Theatre.

Source (checked 2026-10-25): Spektrix ticketing API (https://tickets.parktheatre.co.uk/parktheatre).
Park200, Park90 and the Morris Space; events elsewhere/online and supplementary
items are left out.
"""

from listings.sources.spektrix import SpektrixVenue


class ParkTheatre(SpektrixVenue):
    slug = "park-theatre"
    name = "Park Theatre"
    api_base = "https://tickets.parktheatre.co.uk/parktheatre"
    info_page = "https://parktheatre.co.uk/whats-on/"
    default_category = None
    rules = (
        ('attribute_Venue', r'Elsewhere|Online', None),
        ('attribute_Genre', r'Supplementary', None),
        ('attribute_Genre', r'Stand-up', 'comedy'),
        ('attribute_Genre', r'Drama|Comedy|Musical|One-off', 'theatre'),
    )


VENUE = ParkTheatre()
