"""Cafe Oto (Dalston).

Source (checked 2026-10-24): own site, no JSON-LD or feeds; /events/ is
server-rendered and paginated (?page=2, ...):

  div.each-activity
    .each-header p                     "Sunday 25 October 2026, 7.30pm"
    .each-image img                    image
    .each-header p a[href=/events/..]  title, e.g. "Carl Stone + Excel DJ + Silvia Kastel (DJ)"
    .each-price span                   prices ("£17", "£15 Advance", "£10 MEMBERS")
"""

from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from listings.http import PoliteClient
from listings.model import LONDON, Showing, london_iso
from listings.text import guess_lineup, parse_clock, tidy_title
from listings.venues.base import Venue

SITE = "https://www.cafeoto.co.uk"
MAX_PAGES = 12
_WHEN = re.compile(r"^\w+day\s+(\d{1,2}\s+\w+\s+\d{4}),\s*(.+)$")


class CafeOto(Venue):
    slug = "cafe-oto"
    name = "Cafe Oto"
    source_description = f"Server-rendered, paginated event list ({SITE}/events/)"

    def fetch(self, client: PoliteClient) -> list[Showing]:
        now = datetime.now(LONDON)
        showings = {}
        url = SITE + "/events/"
        for _ in range(MAX_PAGES):
            soup = BeautifulSoup(client.get(url).text, "html.parser")
            for block in soup.select("div.each-activity"):
                headers = block.select(".each-header p")
                link = block.select_one(".each-header p a[href]")
                if len(headers) < 2 or link is None:
                    continue
                m = _WHEN.match(headers[0].get_text(" ", strip=True))
                if not m:
                    continue
                day = datetime.strptime(m.group(1), "%d %B %Y").date()
                t = parse_clock(m.group(2).split("–")[0].split("-")[0].strip())
                if t is None:
                    continue
                start = datetime.combine(day, t, tzinfo=LONDON)
                if start < now:
                    continue
                title = tidy_title(link.get_text(" ", strip=True))
                price_el = block.select_one(".each-price")
                price_text = " ".join(
                    sp.get_text(" ", strip=True) for sp in (price_el.select("span") if price_el else [])
                    if "member" not in sp.get_text().lower()
                )
                prices = [float(p) for p in re.findall(r"£(\d+(?:\.\d\d)?)", price_text)]
                img = block.select_one(".each-image img")
                key = link["href"].strip("/").rsplit("/", 1)[-1]
                showings[key] = Showing(
                    id=f"{self.slug}:{key}",
                    venue=self.name,
                    category="music",
                    title=title,
                    start=london_iso(start),
                    runtime_minutes=None,
                    lineup=[re.sub(r"\s*\((?:DJ|dj)\)$", "", a) for a in guess_lineup(title)],
                    price=f"From £{min(prices):g}" if prices else None,
                    booking_url=urljoin(SITE, link["href"]),
                    image_url=img.get("src") if img else None,
                    tags=["dj"] if "(DJ)" in title else [],
                )
            nxt = soup.select_one('#iscroll_other a[href*="page="]')
            if nxt is None:
                break
            url = urljoin(SITE + "/events/", nxt["href"])
        if not showings:
            raise ValueError("no events parsed from Cafe Oto's event list")
        return sorted(showings.values(), key=lambda s: (s.start, s.title))


VENUE = CafeOto()
