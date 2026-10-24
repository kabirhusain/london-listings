"""The Lexi.

Source (checked 2026-10-24): Savoy Systems; the What's On page embeds the whole
programme as JSON (`var Events = {...}`). See listings/sources/savoy.py.
"""

from listings.sources.savoy import SavoyVenue


class TheLexi(SavoyVenue):
    slug = "the-lexi"
    name = "The Lexi"
    whats_on_url = "https://thelexicinema.co.uk/TheLexiCinema.dll/WhatsOn"


VENUE = TheLexi()
