"""Curzon Bloomsbury.

Source (checked 2026-10-24): curzon.com serves a Cloudflare bot challenge
(HTTP 403, even for robots.txt). We don't bypass it, so we use Clusterflick's
open data (CC BY 4.0) for this venue.
"""

from listings.sources.clusterflick import ClusterflickVenue


class CurzonBloomsbury(ClusterflickVenue):
    slug = "curzon-bloomsbury"
    name = "Curzon Bloomsbury"
    clusterflick_id = "curzon.com-bloomsbury"
    exclude_screens = ("Bertha Dochouse",)  # listed as its own venue, bertha_dochouse.py


VENUE = CurzonBloomsbury()
