"""Almeida Theatre (Islington). Run entries: dates per production, no times.

Source (checked 2026-10-25): performance times are only on the ticketing site
(ticketing.almeida.co.uk, Tessitura), which is behind Imperva Incapsula, so we
don't use it. The theatre's own site lists productions on /whats-on/, and each
production page gives its run, e.g. "Tue 10 Nov – Wed 23 Dec 2026". Productions
with only vague dates ("Jun - Jul 2027", "Early 2028") are left out, as are
tours, dinners and other non-performances.
"""

from __future__ import annotations

import re
from datetime import datetime

from bs4 import BeautifulSoup

from listings.http import PoliteClient
from listings.model import LONDON
from listings.sources.runs import run_showing
from listings.text import page_description, parse_date_range, tidy_title
from listings.venues.base import Venue

SITE = "https://almeida.co.uk"
PAGE_MAX_AGE = 24 * 3600
_NOT_A_SHOW = re.compile(r"theatre-tour|\btour\b|dinner|out-there", re.I)


class AlmeidaTheatre(Venue):
    slug = "almeida-theatre"
    name = "Almeida Theatre"
    source_description = f"Production pages on {SITE} (run dates only; ticketing site is bot-protected)"

    def fetch(self, client: PoliteClient):
        listing = BeautifulSoup(client.get(f"{SITE}/whats-on/").text, "html.parser")
        pages = sorted({a["href"] for a in listing.find_all("a", href=True)
                        if re.match(rf"{re.escape(SITE)}/whats-on/[a-z0-9-]+/?$", a["href"])})
        today = datetime.now(LONDON).date()
        showings = []
        for url in pages:
            if _NOT_A_SHOW.search(url):
                continue
            soup = BeautifulSoup(client.get(url, max_age=PAGE_MAX_AGE).text, "html.parser")
            text = soup.get_text(" ", strip=True)
            details = text.split("Event details", 1)[1][:200] if "Event details" in text else text[:400]
            dates = parse_date_range(details)
            if not dates or dates[1] < today:
                continue
            og_title = soup.find("meta", property="og:title")
            title = tidy_title((og_title["content"] if og_title else url.rstrip("/").rsplit("/", 1)[-1]).split(" | ")[0])
            og_image = soup.find("meta", property="og:image")
            showings.append(run_showing(
                self.slug, self.name, title=title, first=dates[0], last=dates[1], url=url,
                image_url=og_image["content"] if og_image else None,
                description=page_description(soup),
                tags=["sold-out"] if re.search(r"Event details\s+Sold Out", text) else [],
            ))
        if not showings:
            raise ValueError("no current or upcoming runs parsed from almeida.co.uk")
        return sorted(showings, key=lambda s: s.start)


VENUE = AlmeidaTheatre()
