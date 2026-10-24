"""Regent Street Cinema.

Source choice (checked 2026-10-24):
- regentstreetcinema.com is a JavaScript app (INDY Cinema Group platform). The
  HTML is an empty shell: no showtimes, no Event JSON-LD, no feeds.
- All its data comes from /graphql, which robots.txt disallows, so we don't use it.
- Clusterflick publishes this venue's listings as open data, so we use that.
"""

from listings.sources.clusterflick import ClusterflickVenue


class RegentStreetCinema(ClusterflickVenue):
    slug = "regent-street-cinema"
    name = "Regent Street Cinema"
    clusterflick_id = "regentstreetcinema.com"


VENUE = RegentStreetCinema()
