"""Ciné Lumière (Institut français, South Kensington).

Source (checked 2026-10-24): the cinema's what's-on URL redirects to the
Institut's general agenda, which shows only today's mixed events in HTML; the
full programme is loaded from an API (iflondres.aec.app) using a key embedded
in the page, which we don't reuse. The Savoy booking site has no What's On page.
Clusterflick publishes the cinema's screenings (CC BY 4.0), with Savoy booking
links, so we use that.
"""

from listings.sources.clusterflick import ClusterflickVenue


class CineLumiere(ClusterflickVenue):
    slug = "cine-lumiere"
    name = "Ciné Lumière"
    clusterflick_id = "institut-francais.org.uk"


VENUE = CineLumiere()
