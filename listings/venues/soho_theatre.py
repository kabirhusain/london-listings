"""Soho Theatre.

Source (checked 2026-10-25): Spektrix ticketing API (https://tickets.sohotheatre.com/sohotheatre).
Only Dean Street (Upstairs/Downstairs/Theatre/Studio); Soho Theatre
Walthamstow, the Soho Player streams and touring dates are left out. Podcasts
are left out.
"""

from listings.sources.spektrix import SpektrixVenue


class SohoTheatre(SpektrixVenue):
    slug = "soho-theatre"
    name = "Soho Theatre"
    api_base = "https://tickets.sohotheatre.com/sohotheatre"
    info_page = "https://sohotheatre.com/whats-on/"
    default_category = None
    rules = (
        ('attribute_Venue', r'Walthamstow|Soho Player|Glasgow|Glee Club', None),
        ('attribute_WebsiteFilterCategory1', r'^(?:Comedy|Cabaret)$', 'comedy'),
        ('attribute_WebsiteFilterCategory1', r'^(?:Theatre|Family)$', 'theatre'),
        ('attribute_WebsiteFilterCategory1', r'^Music$', 'music'),
    )


VENUE = SohoTheatre()
