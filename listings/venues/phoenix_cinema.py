"""Phoenix Cinema.

Source (checked 2026-10-24): Savoy Systems; the What's On page embeds the whole
programme as JSON (`var Events = {...}`). See listings/sources/savoy.py.
"""

from listings.sources.savoy import SavoyVenue


class PhoenixCinema(SavoyVenue):
    slug = "phoenix-cinema"
    name = "Phoenix Cinema"
    whats_on_url = "https://www.phoenixcinema.co.uk/PhoenixCinemaLondon.dll/WhatsOn"


VENUE = PhoenixCinema()
