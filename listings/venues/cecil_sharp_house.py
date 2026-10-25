"""Cecil Sharp House (English Folk Dance and Song Society).

Source (checked 2026-10-24): the what's-on page (efdss.org) is rendered by
JavaScript. EFDSS also has RSS/Atom feeds, but its Spektrix API
(sales.efdss.org/efdss) is more structured and includes a doors time per
performance. We use the API.

Included: concerts (attribute_TAAArtform "Music") and ceilidhs/barn dances
(live bands). Left out: classes (Morris, English Country Dancing), education
days, talks.
"""

import re

from listings.sources.spektrix import SpektrixVenue, parse_doors, spektrix_utc
from listings.text import guess_lineup

_SOCIAL_DANCE = re.compile(r"ceilidh|barn ?dance", re.I)
_NOT_A_GIG = re.compile(r"workshop|course|class|development day|training|zoom", re.I)


class CecilSharpHouse(SpektrixVenue):
    slug = "cecil-sharp-house"
    name = "Cecil Sharp House"
    api_base = "https://sales.efdss.org/efdss"

    def info_url(self, event):
        # EFDSS's site resolves /whats-on/<id> to the event page, and the Spektrix
        # events carry that id in attribute_CMSID (checked: 16024 -> Elanor Moss).
        cms = (event.get("attribute_CMSID") or "").strip()
        return f"https://www.efdss.org/whats-on/{cms}" if cms.isdigit() else None

    def category(self, event, instance):
        name = event["name"]
        if _NOT_A_GIG.search(name):
            return None
        if event.get("attribute_TAAArtform") == "Music" or _SOCIAL_DANCE.search(name):
            return "music"
        return None

    def details(self, event, instance, category):
        dance = bool(_SOCIAL_DANCE.search(event["name"]))
        return {
            "genre": "Ceilidh" if dance else "Folk",
            "lineup": [] if dance else guess_lineup(event["name"]),
            "doors": parse_doors(instance.get("attribute_Doors"), spektrix_utc(instance["startUtc"])),
            "tags": ["ceilidh"] if dance else [],
        }


VENUE = CecilSharpHouse()
