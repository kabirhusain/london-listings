"""Orange Tree Theatre.

Source (checked 2026-10-25): Spektrix ticketing API (https://tickets.orangetreetheatre.co.uk/orangetree).
Plays and recitals; seminars, talks and streamed ("On Screen") performances are
left out.
"""

from listings.sources.spektrix import SpektrixVenue


class OrangeTreeTheatre(SpektrixVenue):
    slug = "orange-tree-theatre"
    name = "Orange Tree Theatre"
    api_base = "https://tickets.orangetreetheatre.co.uk/orangetree"
    info_page = "https://orangetreetheatre.co.uk/whats-on/"
    default_category = None
    rules = (
        ('name', r'on screen|seminar', None),
        ('attribute_Type', r'Play|Drama|Musical', 'theatre'),
        ('attribute_Type', r'Chamber|Recital|Concert', 'music'),
    )


VENUE = OrangeTreeTheatre()
