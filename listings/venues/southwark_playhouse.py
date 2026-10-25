"""Southwark Playhouse.

Source (checked 2026-10-25): Spektrix ticketing API (https://tickets.southwarkplayhouse.co.uk/southwarkplayhouse).
Writers' groups are left out.
"""

from listings.sources.spektrix import SpektrixVenue


class SouthwarkPlayhouse(SpektrixVenue):
    slug = "southwark-playhouse"
    name = "Southwark Playhouse"
    api_base = "https://tickets.southwarkplayhouse.co.uk/southwarkplayhouse"
    info_page = "https://southwarkplayhouse.co.uk/whats-on/"
    default_category = 'theatre'
    rules = (
        ('name', r'collective|writers', None),
    )


VENUE = SouthwarkPlayhouse()
