"""ICA (Institute of Contemporary Arts).

Source (checked 2026-10-24): ica.art lists films in HTML with dates but no
times. The site's Spektrix web components point at buy.ica.art/ica, whose
public API has every performance. We use that. Events are tagged by the ICA
with attribute_Category ("Films", "Live", ...) and attribute_TAAArtform ("Film",
"Music", ...).
"""

from listings.sources.spektrix import SpektrixVenue
from listings.text import guess_lineup


class ICA(SpektrixVenue):
    slug = "ica"
    name = "ICA"
    api_base = "https://buy.ica.art/ica"
    info_page = "https://www.ica.art/films"

    def category(self, event, instance):
        if event.get("attribute_Category") == "Films" or event.get("attribute_TAAArtform") == "Film":
            return "film"
        if event.get("attribute_TAAArtform") == "Music":
            return "music"
        return None

    def details(self, event, instance, category):
        tags = []
        if instance.get("attribute_Captioned"):
            tags.append("captioned")
        if instance.get("attribute_BSLInterpreted"):
            tags.append("bsl")
        out = {"tags": tags}
        if category == "music":
            sub = event.get("attribute_TAASubGenre") or ""
            out["genre"] = sub.replace(" Music", "") if sub and sub != "Other Music" else None
            out["lineup"] = guess_lineup(event["name"])
        return out


VENUE = ICA()
