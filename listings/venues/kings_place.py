"""Kings Place.

Source (checked 2026-10-24): kingsplace.co.uk serves a JavaScript bot challenge (HTTP 403), even for robots.txt. We don't bypass that. Songkick's venue page
has MusicEvent JSON-LD with performers (paginated). It's crowd-sourced, so it
may miss or lag shows; use manual/ to fill gaps.
"""

from listings.sources.jsonld import JsonLdEventsVenue


class KingsPlace(JsonLdEventsVenue):
    slug = "kings-place"
    name = "Kings Place"
    page_url = "https://www.songkick.com/venues/47963-kings-place/calendar"
    title_suffix = "@ Kings Place"
    max_pages = 3
    genre = None


VENUE = KingsPlace()
