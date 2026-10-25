"""The Troubadour (Earl's Court).

Source (checked 2026-10-24): the venue moved to troubadourlondon.com (the old
troubadour.co.uk domain now redirects to an unrelated loans site). It's a Wix
site; /all-events embeds the Wix Events data as JSON in
<script id="wix-warmup-data">: each event has title, slug,
scheduling.config.startDate (UTC), mainImage and an external ticket link
(Ticketweb / DICE / Universe / Eventbrite).
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from listings.http import PoliteClient
from listings.model import Showing, london_iso
from listings.text import guess_lineup, tidy_title
from listings.venues.base import Venue

SITE = "https://www.troubadourlondon.com"
URL = SITE + "/all-events"
_PRESENTED = re.compile(r"\s+presented by .*$", re.I)


class TheTroubadour(Venue):
    slug = "the-troubadour"
    name = "The Troubadour"
    source_description = f"Wix Events JSON embedded in {URL}"

    def fetch(self, client: PoliteClient) -> list[Showing]:
        html = client.get(URL).text
        m = re.search(r'<script[^>]*id="wix-warmup-data"[^>]*>(.*?)</script>', html, re.S)
        if not m:
            raise ValueError("no wix-warmup-data on the Troubadour events page")
        events = {}

        def walk(node):
            if isinstance(node, dict):
                if "scheduling" in node and "title" in node and "slug" in node:
                    events[node.get("id") or node["slug"]] = node
                    return
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)

        walk(json.loads(m.group(1)))
        now = datetime.now(timezone.utc)
        showings = []
        for key, ev in events.items():
            cfg = (ev.get("scheduling") or {}).get("config") or {}
            if cfg.get("scheduleTbd") or not cfg.get("startDate"):
                continue
            start = datetime.fromisoformat(cfg["startDate"].replace("Z", "+00:00"))
            if start < now:
                continue
            title = tidy_title(_PRESENTED.sub("", ev["title"]))
            reg = ev.get("registration") or {}
            external = (reg.get("external") or {}).get("registration")
            sold_out = bool((reg.get("ticketing") or {}).get("soldOut"))
            showings.append(Showing(
                id=f"{self.slug}:{key}",
                venue=self.name,
                category="music",
                title=title,
                start=london_iso(start),
                runtime_minutes=None,
                lineup=guess_lineup(title),
                booking_url=external or f"{SITE}/event-details/{ev['slug']}",
                image_url=(ev.get("mainImage") or {}).get("url") or None,
                tags=["sold-out"] if sold_out else [],
                description=ev.get("description"),
            ))
        if not showings:
            raise ValueError("no upcoming events in the Troubadour's Wix data")
        return sorted(showings, key=lambda s: (s.start, s.title))


VENUE = TheTroubadour()
