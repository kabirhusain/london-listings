"""Curzon Soho.

Source (checked 2026-10-24): curzon.com serves a Cloudflare bot challenge
(HTTP 403, even for robots.txt). We don't bypass it, so we use Clusterflick's
open data (CC BY 4.0) for this venue.
"""

from listings.sources.clusterflick import ClusterflickVenue


class CurzonSoho(ClusterflickVenue):
    slug = "curzon-soho"
    name = "Curzon Soho"
    clusterflick_id = "curzon.com-soho"


VENUE = CurzonSoho()
