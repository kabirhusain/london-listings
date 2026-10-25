"""The Nickel (Clerkenwell).

Source (checked 2026-10-24): Next.js site with no JSON-LD, feeds or JSON
endpoint found; the homepage server-renders every screening:

  a[href="/screening/<id>"]
    img[alt="Poster for <TITLE>"]
    p.font-bold                       TITLE
    "Runtime: 94 mins", "Certificate: 15"
    "Sunday 25/10", "Bar 1:00pm", "Film 1:30pm", format, "Sold Out"
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from listings.http import PoliteClient
from listings.model import LONDON, Showing, london_iso
from listings.text import tidy_title
from listings.venues.base import Venue

SITE = "https://thenickel.co.uk"
_DATE = re.compile(r"\b(\d{1,2})/(\d{1,2})\b")
_TIME = r"(\d{1,2}(?::\d{2})?\s*[ap]m)"


class TheNickel(Venue):
    slug = "the-nickel"
    name = "The Nickel"
    source_description = f"Server-rendered homepage ({SITE}/)"

    def fetch(self, client: PoliteClient) -> list[Showing]:
        soup = BeautifulSoup(client.get(SITE + "/").text, "html.parser")
        now = datetime.now(LONDON)
        showings = {}
        for a in soup.select('a[href^="/screening/"]'):
            text = a.get_text("\n", strip=True)
            title_el = a.select_one("p.font-bold")
            date_m = _DATE.search(text)
            film_m = re.search(rf"Film\s*{_TIME}", text, re.I)
            if not (title_el and date_m and film_m):
                continue
            day = _infer_date(int(date_m.group(1)), int(date_m.group(2)), now)
            start = datetime.combine(day, _clock(film_m.group(1)), tzinfo=LONDON)
            if start < now:
                continue
            bar_m = re.search(rf"Bar\s*{_TIME}", text, re.I)
            doors = datetime.combine(day, _clock(bar_m.group(1)), tzinfo=LONDON) if bar_m else None
            runtime = re.search(r"Runtime:\s*(\d+)", text)
            cert = re.search(r"Certificate:\s*([\w*]+)", text)
            tags = [f"cert:{cert.group(1)}"] if cert else []
            for fmt in ("35mm", "16mm", "70mm"):
                if re.search(rf"^\s*{fmt}\s*$", text, re.I | re.M):
                    tags.append(fmt)
            if re.search(r"sold out", text, re.I):
                tags.append("sold-out")
            img = a.select_one("img")
            synopsis = a.select_one("div.whitespace-pre-wrap")
            key = a["href"].rstrip("/").rsplit("/", 1)[-1]
            showings[key] = Showing(
                id=f"{self.slug}:{key}",
                venue=self.name,
                category="film",
                title=tidy_title(title_el.get_text(" ", strip=True)),
                start=london_iso(start),
                doors=london_iso(doors) if doors and doors <= start else None,
                runtime_minutes=int(runtime.group(1)) if runtime else None,
                booking_url=urljoin(SITE, a["href"]),
                image_url=img.get("src") if img else None,
                tags=tags,
                description=str(synopsis) if synopsis else None,
            )
        if not showings:
            raise ValueError("no screenings parsed from The Nickel homepage")
        return sorted(showings.values(), key=lambda s: (s.start, s.title))


def _clock(s: str):
    s = s.replace(" ", "").lower()
    return datetime.strptime(s, "%I:%M%p" if ":" in s else "%I%p").time()


def _infer_date(day: int, month: int, now: datetime):
    """'25/10' -> the next such date (this year, or next year if already past)."""
    for year in (now.year, now.year + 1):
        try:
            d = datetime(year, month, day).date()
        except ValueError:
            continue
        if d >= (now - timedelta(days=1)).date():
            return d
    return datetime(now.year, month, day).date()


VENUE = TheNickel()
