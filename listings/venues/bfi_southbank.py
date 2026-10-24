"""BFI Southbank.

Source choice (checked 2026-10-24):
- whatson.bfi.org.uk (the AudienceView ticketing site that holds the listings)
  serves a Cloudflare managed challenge to non-browser clients, and its
  robots.txt disallows /WebAPI/. We don't try to get past the challenge.
- www.bfi.org.uk is reachable but only has editorial content: no showtimes,
  no Event JSON-LD, and its RSS feed is features/reviews only.
- Clusterflick publishes BFI Southbank listings as clean, licensed JSON, so we
  use that.
"""

from listings.sources.clusterflick import ClusterflickVenue


class BFISouthbank(ClusterflickVenue):
    slug = "bfi-southbank"
    name = "BFI Southbank"
    clusterflick_id = "bfi.org.uk-southbank"


VENUE = BFISouthbank()
