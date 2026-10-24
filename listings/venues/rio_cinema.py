"""Rio Cinema.

Source (checked 2026-10-24): Savoy Systems; the What's On page embeds the whole
programme as JSON (`var Events = {...}`). See listings/sources/savoy.py.
"""

from listings.sources.savoy import SavoyVenue


class RioCinema(SavoyVenue):
    slug = "rio-cinema"
    name = "Rio Cinema"
    whats_on_url = "https://riocinema.org.uk/Rio.dll/WhatsOn"


VENUE = RioCinema()
