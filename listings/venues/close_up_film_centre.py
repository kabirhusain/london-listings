"""Close-Up Film Centre.

Source (checked 2026-10-24): closeupfilmcentre.com serves a Cloudflare bot challenge
(HTTP 403, even for robots.txt). We don't bypass it, so we use Clusterflick's
open data (CC BY 4.0) for this venue.
"""

from listings.sources.clusterflick import ClusterflickVenue


class CloseUpFilmCentre(ClusterflickVenue):
    slug = "close-up-film-centre"
    name = "Close-Up Film Centre"
    clusterflick_id = "closeupfilmcentre.com"


VENUE = CloseUpFilmCentre()
