"""Bertha DocHouse (inside Curzon Bloomsbury).

Source (checked 2026-10-24): dochouse.org lists films with dates but puts
times on each film's page, and tickets are sold by Curzon (whose site is
behind a Cloudflare challenge). Clusterflick's Curzon Bloomsbury data (CC BY
4.0) includes DocHouse's own screen, so we take the "Bertha Dochouse" screen
from it (one request, shared with curzon_bloomsbury.py via the cache).
"""

from listings.sources.clusterflick import ClusterflickVenue


class BerthaDocHouse(ClusterflickVenue):
    slug = "bertha-dochouse"
    name = "Bertha DocHouse"
    clusterflick_id = "curzon.com-bloomsbury"
    only_screens = ("Bertha Dochouse",)
    title_prefix = "DocHouse:"


VENUE = BerthaDocHouse()
