"""Check a venue page for structured listing sources before writing a scraper.

    python -m listings probe https://www.example-cinema.co.uk/whats-on

Reports: whether robots.txt allows the page, schema.org Event JSON-LD, feed
links (RSS/Atom/iCal), and signs of a ticketing platform whose data the page
loads.
"""

from __future__ import annotations

import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from listings.http import BlockedByChallenge, FetchError, PoliteClient

# Strings in page source that point at a ticketing platform and its data.
PLATFORM_HINTS = {
    "AudienceView (articleContext JSON in page)": r"articleContext\s*=",
    "Spektrix": r"spektrix",
    "Veezi": r"veezi",
    "Admit One": r"admit-one|admitone",
    "Savoy Systems / INDY": r"savoysystems|indy\.systems",
    "Ticketsolve": r"ticketsolve",
    "Tessitura": r"tessitura|tnew",
    "Eventive": r"eventive\.org",
    "Jack Roe (RTS)": r"jack[- ]?roe|rts-sa\.com",
    "Vista (OCAPI)": r"ocapi|vista\.co",
    "Next.js data (__NEXT_DATA__)": r"__NEXT_DATA__",
}

FEED_TYPES = ("application/rss+xml", "application/atom+xml", "text/calendar")


def probe(url: str, client: PoliteClient | None = None) -> dict:
    client = client or PoliteClient()
    report: dict = {"url": url}
    try:
        resp = client.get(url)
    except BlockedByChallenge as e:
        return {**report, "blocked": str(e)}
    except FetchError as e:
        return {**report, "error": str(e)}

    soup = BeautifulSoup(resp.text, "html.parser")
    report["jsonld_events"] = _count_jsonld_events(soup)
    report["feeds"] = [
        urljoin(resp.url, link["href"])
        for link in soup.find_all("link", href=True)
        if link.get("type") in FEED_TYPES
    ] + sorted({
        urljoin(resp.url, a["href"])
        for a in soup.find_all("a", href=True)
        if re.search(r"\.ics(\?|$)|webcal:|/feed/?$|/rss", a["href"])
    })
    report["platforms"] = [
        name for name, pattern in PLATFORM_HINTS.items() if re.search(pattern, resp.text, re.I)
    ]
    return report


def _count_jsonld_events(soup: BeautifulSoup) -> int:
    count = 0
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except json.JSONDecodeError:
            continue
        count += sum(1 for item in _walk(data) if _is_event(item))
    return count


def _walk(node):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v)


def _is_event(item: dict) -> bool:
    types = item.get("@type", [])
    types = types if isinstance(types, list) else [types]
    return any(str(t).endswith(("Event", "ScreeningEvent")) for t in types)
