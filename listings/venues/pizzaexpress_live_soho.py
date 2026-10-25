"""PizzaExpress Live (Soho Jazz Club).

Source (checked 2026-10-24): the site is a Next.js app. It reads from a public
JSON API (api.pizzaexpresslive.com, Hydra/JSON-LD, no key needed);
/products/search-event-information lists every venue's shows with doors and
start times, price and image. We keep location "Soho". Dates have no year
("Saturday 24th October"), so the year is inferred.
"""

from __future__ import annotations

from datetime import datetime

from listings.http import PoliteClient
from listings.model import LONDON, Showing, london_iso
from listings.text import date_without_year, guess_lineup, tidy_title
from listings.venues.base import Venue

API = "https://api.pizzaexpresslive.com"
MAX_PAGES = 30


class PizzaExpressLiveSoho(Venue):
    slug = "pizzaexpress-live-soho"
    name = "PizzaExpress Live Soho"
    location = "Soho"
    source_description = f"PizzaExpress Live JSON API ({API}/products/search-event-information)"

    def fetch(self, client: PoliteClient) -> list[Showing]:
        today = datetime.now(LONDON).date()
        now = datetime.now(LONDON)
        showings = {}
        url = f"{API}/products/search-event-information?page=1"
        for _ in range(MAX_PAGES):
            data, _ = client.get_json(url)
            for e in data.get("hydra:member", []):
                if (e.get("location") or "").strip().lower() != self.location.lower():
                    continue
                day = date_without_year(e.get("eventDate") or "", today)
                start_t = _time(e.get("showStartTime"))
                if day is None or start_t is None:
                    continue
                start = datetime.combine(day, start_t, tzinfo=LONDON)
                if start < now:
                    continue
                doors_t = _time(e.get("doorsOpenTime"))
                doors = datetime.combine(day, doors_t, tzinfo=LONDON) if doors_t else None
                title = tidy_title(e["name"])
                pence = e.get("price")
                showings[e["id"]] = Showing(
                    id=f"{self.slug}:{e['id']}",
                    venue=self.name,
                    category="music",
                    title=title,
                    start=london_iso(start),
                    doors=london_iso(doors) if doors and doors <= start else None,
                    runtime_minutes=None,
                    lineup=guess_lineup(title),
                    genre="Jazz",
                    price=(f"From £{pence / 100:.2f}".replace(".00", "") if pence else None),
                    booking_url=f"https://www.pizzaexpresslive.com/whats-on/{e['slug']}",
                    image_url=e.get("imageUri") or None,
                    tags=["sold-out"] if e.get("seatAvailable") == 0 else [],
                    description=e.get("description") or None,
                )
            nxt = (data.get("hydra:view") or {}).get("hydra:next")
            if not nxt:
                break
            url = API + nxt
        if not showings:
            raise ValueError("no upcoming Soho shows in the PizzaExpress Live API")
        return sorted(showings.values(), key=lambda s: (s.start, s.title))


def _time(text):
    if not text:
        return None
    for fmt in ("%I:%M%p", "%I%p", "%H:%M"):
        try:
            return datetime.strptime(text.strip().upper().replace(" ", ""), fmt).time()
        except ValueError:
            continue
    return None


VENUE = PizzaExpressLiveSoho()
