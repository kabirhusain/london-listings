"""Bush Hall.

Source (checked 2026-10-24): bushhallmusic.co.uk answers every page request with HTTP 429 (Cloudflare rate limit), even the first. We don't bypass that. Songkick's venue page
has MusicEvent JSON-LD with performers (paginated). It's crowd-sourced, so it
may miss or lag shows; use manual/ to fill gaps.
"""

from listings.sources.jsonld import JsonLdEventsVenue


class BushHall(JsonLdEventsVenue):
    slug = "bush-hall"
    name = "Bush Hall"
    page_url = "https://www.songkick.com/venues/17541-bush-hall/calendar"
    title_suffix = "@ Bush Hall"
    max_pages = 3
    genre = None


VENUE = BushHall()
