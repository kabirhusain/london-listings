"""Genesis Cinema (Mile End).

Source (checked 2026-10-24): Admit One ticketing; no JSON-LD, feeds or JSON
endpoint. The homepage server-renders a panel per date:

  div.whatson_panel#panel_YYYYMMDD
    div.grid-container-border               one film
      h2 a[href=event/<id>]                 title
      img[src=/ratings/UK/<cert>lrg.png]    certificate
      "Running time: <span>129 mins</span>"
      a.perfButton[href=...perfCode=<n>]    one performance: time text, icon alt = type
"""

from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from listings.http import PoliteClient
from listings.model import LONDON, Showing, london_iso
from listings.text import tidy_title
from listings.venues.base import Venue

URL = "https://www.genesiscinema.co.uk/"
_PERF = re.compile(r"perfCode=(\d+)")


class GenesisCinema(Venue):
    slug = "genesis-cinema"
    name = "Genesis Cinema"
    source_description = f"Server-rendered homepage ({URL})"

    def fetch(self, client: PoliteClient) -> list[Showing]:
        soup = BeautifulSoup(client.get(URL).text, "html.parser")
        now = datetime.now(LONDON)
        showings = {}
        for panel in soup.select("div.whatson_panel"):
            m = re.match(r"panel_(\d{8})$", panel.get("id") or "")
            if not m:
                continue
            day = datetime.strptime(m.group(1), "%Y%m%d").date()
            for film in panel.select("div.grid-container-border"):
                link = film.select_one("h2 a")
                if link is None:
                    continue
                title = tidy_title(link.get_text(" ", strip=True))
                img = film.select_one("img[src*='customFilmImages'], img.object-contain")
                rating = film.select_one("img[src*='/ratings/']")
                runtime = re.search(r"Running time:\s*(\d+)\s*mins", film.get_text(" ", strip=True))
                synopsis = film.select_one("p.py-3")
                if synopsis:
                    for more in synopsis.find_all("a"):
                        more.extract()
                for a in film.select("a.perfButton[href*='perfCode']"):
                    perf = _PERF.search(a["href"]).group(1)
                    t = re.search(r"\b(\d{1,2}:\d{2})\b", a.get_text(" ", strip=True))
                    if not t:
                        continue
                    start = datetime.combine(day, datetime.strptime(t.group(1), "%H:%M").time(), tzinfo=LONDON)
                    if start < now:
                        continue
                    tags = [f"cert:{rating['alt']}"] if rating and rating.get("alt") else []
                    tags += [_kebab(i["alt"].replace(" icon", "")) for i in a.select("img[alt]") if i.get("alt")]
                    if "soldOut" in " ".join(a.get("class", [])) or "line-through" in (a.get("style") or ""):
                        tags.append("sold-out")
                    showings[perf] = Showing(
                        id=f"{self.slug}:{perf}",
                        venue=self.name,
                        category="film",
                        title=title,
                        start=london_iso(start),
                        runtime_minutes=int(runtime.group(1)) if runtime else None,
                        booking_url=a["href"],
                        image_url=urljoin(URL, img["src"]) if img and img.get("src") else None,
                        tags=list(dict.fromkeys(tags)),
                        description=synopsis.get_text(" ", strip=True) if synopsis else None,
                    )
        if not showings:
            raise ValueError("no performances parsed from the Genesis homepage")
        return sorted(showings.values(), key=lambda s: (s.start, s.title))


def _kebab(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


VENUE = GenesisCinema()
