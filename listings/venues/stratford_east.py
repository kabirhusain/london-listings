"""Theatre Royal Stratford East.

Source (checked 2026-10-25): Spektrix ticketing API (https://tickets.stratfordeast.com/stratfordeast).
Only productions (classes such as "SES Sep - Dec" are left out).
"""

from listings.sources.spektrix import SpektrixVenue


class StratfordEast(SpektrixVenue):
    slug = "stratford-east"
    name = "Theatre Royal Stratford East"
    api_base = "https://tickets.stratfordeast.com/stratfordeast"
    info_page = "https://www.stratfordeast.com/whats-on"
    default_category = None
    rules = (
        ('attribute_WebsiteChannel', r'^Production$', 'theatre'),
    )


VENUE = StratfordEast()
