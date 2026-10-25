"""Donmar Warehouse.

Source (checked 2026-10-25): Spektrix ticketing API (https://tickets.donmarwarehouse.com/donmarwarehouse).
Only events tagged Website=Performance (not development events).
"""

from listings.sources.spektrix import SpektrixVenue


class DonmarWarehouse(SpektrixVenue):
    slug = "donmar-warehouse"
    name = "Donmar Warehouse"
    api_base = "https://tickets.donmarwarehouse.com/donmarwarehouse"
    default_category = None
    rules = (
        ('attribute_Website', r'^Performance$', 'theatre'),
    )


VENUE = DonmarWarehouse()
