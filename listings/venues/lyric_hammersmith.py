"""Lyric Hammersmith.

Source (checked 2026-10-25): Spektrix ticketing API (https://tickets.lyric.co.uk/lyrichammersmith).
Young people's programme (YPBOC / Youth Arts Festival workshops) and access
events are left out.
"""

from listings.sources.spektrix import SpektrixVenue


class LyricHammersmith(SpektrixVenue):
    slug = "lyric-hammersmith"
    name = "Lyric Hammersmith"
    api_base = "https://tickets.lyric.co.uk/lyrichammersmith"
    default_category = None
    rules = (
        ('attribute_Programme', r'YPBOC', None),
        ('name', r'^YAF:', None),
        ('attribute_Type', r'Access', None),
        ('attribute_Type', r'^Music$', 'music'),
        ('attribute_Type', r'^Comedy$', 'comedy'),
        ('attribute_Type', r'Main House|Children|For The Culture|Studio', 'theatre'),
    )


VENUE = LyricHammersmith()
