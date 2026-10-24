"""Ronnie Scott's.

Source (checked 2026-10-24): ronniescotts.co.uk serves a Cloudflare bot challenge (HTTP 403). We don't bypass that. Songkick's venue page
has MusicEvent JSON-LD with performers (paginated). It's crowd-sourced, so it
may miss or lag shows; use manual/ to fill gaps.
"""

from listings.sources.jsonld import JsonLdEventsVenue


class RonnieScotts(JsonLdEventsVenue):
    slug = "ronnie-scotts"
    name = "Ronnie Scott's"
    page_url = "https://www.songkick.com/venues/36418-ronnie-scotts-jazz-club/calendar"
    title_suffix = "@ Ronnie Scott's Jazz Club"
    max_pages = 6
    genre = "Jazz"


VENUE = RonnieScotts()
