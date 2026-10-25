"""Barbican Centre: theatre, dance and concerts (films are in barbican_cinema.py).

Source (checked 2026-10-25): the same Spektrix API as barbican_cinema.py
(spektrix.barbican.org.uk/barbicancentre); the responses are cached, so this
adds no requests. Uses attribute_PrimaryArtForm / attribute_EventType /
attribute_EventGenre. LSO St Luke's and Guildhall School (GSMD) events are
other venues and are left out, as are talks, workshops and tours.
"""

from listings.sources.spektrix import SpektrixVenue


class BarbicanCentre(SpektrixVenue):
    slug = "barbican-centre"
    name = "Barbican Centre"
    api_base = "https://spektrix.barbican.org.uk/barbicancentre"
    rules = (
        ("attribute_Lsosite", r"^True$", None),
        ("attribute_GSMDEvent", r"^True$", None),
        ("attribute_EventType", r"Talk|Workshop|Tour|Participatory|Ceremony|Conservatory", None),
        ("attribute_EventGenre", r"Dance", "dance"),
        ("attribute_PrimaryArtForm", r"^Theatre$", "theatre"),
        ("attribute_PrimaryArtForm", r"^(?:Classical|Contemporary) Music$", "music"),
    )

    def booking_url(self, instance):
        from listings.sources.spektrix import instance_number
        return f"https://tickets.barbican.org.uk/choose-seats/{instance_number(instance['id'])}"

    def details(self, event, instance, category):
        out = super().details(event, instance, category)
        genre = event.get("attribute_EventGenre") or None
        if genre and category in ("music", "dance"):
            out["genre"] = genre
        return out


VENUE = BarbicanCentre()
