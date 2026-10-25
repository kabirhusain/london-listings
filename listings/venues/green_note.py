"""Green Note (Camden).

Source (checked 2026-10-24): WordPress; tickets via WeGotTickets. The site's
/upcoming_events URL is an RSS feed of every upcoming show:

  <item><title>Malin Pettersen</title><link>.../production/malin-pettersen/</link>
        <description>25th October 2026. MALIN PETTERSEN: ...</description>
        <content:encoded>... Doors open 7pm. Music starts 8pm. ... £14 ...</content:encoded>
"""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

from listings.http import PoliteClient
from listings.model import LONDON, Showing, london_iso
from listings.text import find_doors_and_start, guess_lineup, tidy_title
from listings.venues.base import Venue

FEED = "https://www.greennote.co.uk/upcoming_events"
_DATE = re.compile(r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(\d{4})")
_CONTENT = "{http://purl.org/rss/1.0/modules/content/}encoded"


class GreenNote(Venue):
    slug = "green-note"
    name = "Green Note"
    source_description = f"RSS feed of upcoming shows ({FEED})"

    def fetch(self, client: PoliteClient) -> list[Showing]:
        root = ET.fromstring(client.get(FEED).text.encode("utf-8"))
        now = datetime.now(LONDON)
        showings = {}
        for item in root.iter("item"):
            title = tidy_title(item.findtext("title") or "")
            link = (item.findtext("link") or "").strip()
            desc = html.unescape(item.findtext("description") or "")
            body = html.unescape(re.sub(r"<[^>]+>", " ", item.findtext(_CONTENT) or ""))
            m = _DATE.search(desc)
            if not (title and m):
                continue
            day = datetime.strptime(" ".join(m.groups()), "%d %B %Y").date()
            doors_t, start_t = find_doors_and_start(body)
            tags = []
            if start_t is None:
                if doors_t is None:
                    continue
                start_t, doors_t = doors_t, None
                tags.append("time-is-doors")
            start = datetime.combine(day, start_t, tzinfo=LONDON)
            if start < now:
                continue
            doors = datetime.combine(day, doors_t, tzinfo=LONDON) if doors_t else None
            if doors and not (start - timedelta(hours=3) <= doors <= start):
                doors = None
            prices = [float(p) for p in re.findall(r"£(\d+(?:\.\d\d)?)", body)]
            img = re.search(r'<img[^>]+src="([^"]+)"', item.findtext(_CONTENT) or "")
            key = link.rstrip("/").rsplit("/", 1)[-1] + f":{start.strftime('%Y%m%dT%H%M')}"
            showings[key] = Showing(
                id=f"{self.slug}:{key}",
                venue=self.name,
                category="music",
                title=title,
                start=london_iso(start),
                doors=london_iso(doors) if doors else None,
                runtime_minutes=None,
                lineup=guess_lineup(re.sub(r"\((?:matin[ée]e|early|late)[^)]*\)", "", title, flags=re.I)),
                price=f"From £{min(prices):g}" if prices else None,
                booking_url=link or None,
                image_url=img.group(1) if img else None,
                tags=tags,
                description=item.findtext(_CONTENT) or desc,
            )
        if not showings:
            raise ValueError("no shows parsed from Green Note's RSS feed")
        return sorted(showings.values(), key=lambda s: (s.start, s.title))


VENUE = GreenNote()
