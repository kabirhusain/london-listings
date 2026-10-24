"""Barbican Cinema.

Source choice (checked 2026-10-24):
- No Event JSON-LD and no feeds on barbican.org.uk.
- The site loads ticketing data from a public Spektrix API
  (https://spektrix.barbican.org.uk/barbicancentre/api/v3; its config is in the
  page's drupalSettings). Two requests (/events and /instances) cover the whole
  Barbican programme, so this is the primary source. It has no robots.txt (404).
- Spektrix has no images or runtimes for these events, and includes some
  internal events (e.g. staff "test screens"). So we also fetch Barbican's own
  cinema listing for a few days (/whats-on/cinema?day=YYYY-MM-DD) and join on
  the performance id in the booking links (tickets.barbican.org.uk/choose-seats/<n>,
  where <n> is the numeric prefix of the Spektrix instance id). That gives the
  image, runtime and page URL, and lets us drop events the public site doesn't list.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from listings.http import FetchError, PoliteClient
from listings.sources.spektrix import fetch_spektrix, instance_number as _instance_number, spektrix_utc as _utc
from listings.model import LONDON, Showing, london_iso
from listings.venues.base import Venue

SPEKTRIX_API = "https://spektrix.barbican.org.uk/barbicancentre/api/v3"
SITE = "https://www.barbican.org.uk"
DAY_LISTING_URL = SITE + "/whats-on/cinema?day={day}"
BOOKING_URL = "https://tickets.barbican.org.uk/choose-seats/{n}"
MAX_DAY_PAGES = 40

# Certificates and access notes that Spektrix appends to event names.
_NAME_NOISE = re.compile(r"\s*\((?:U|PG|12A?|15|18|R18|cert tbc|tbc|AD)\*?\)", re.I)
_RUNTIME = re.compile(r"^(?:(\d+)\s*hrs?)?\s*(?:(\d+)\s*mins?)?$", re.I)
_CHOOSE_SEATS = re.compile(r"choose-seats/(\d+)")
_SHOW_TIME = re.compile(r"(\d{1,2})[.:](\d{2})\s*(am|pm)", re.I)

_EVENT_TYPE_TAGS = {
    "Relaxed Screening": "relaxed",
    "Talk + Screening": "q-and-a",
    "Screening + Workshop": "workshop",
}

_INSTANCE_FLAG_TAGS = {
    "attribute_AudioDescribed": "audio-described",
    "attribute_Captioned": "captioned",
    "attribute_BSL": "bsl",
    "attribute_Relaxed": "relaxed",
    "attribute_TouchTour": "touch-tour",
    "attribute_Preview": "preview",
}


@dataclass
class _WebInfo:
    title: str
    page_url: str | None
    image_url: str | None
    runtime_minutes: int | None


class BarbicanCinema(Venue):
    slug = "barbican-cinema"
    name = "Barbican Cinema"
    source_description = (
        f"Spektrix ticketing API ({SPEKTRIX_API}) for showtimes, "
        f"enriched from {SITE}/whats-on/cinema day listings"
    )

    def __init__(self):
        self._notes: list[str] = []

    def fetch(self, client: PoliteClient) -> list[Showing]:
        self._notes = []
        events, instances = fetch_spektrix(client, SPEKTRIX_API.removesuffix("/api/v3"), datetime.now(LONDON).date())
        cinema_events = {k: e for k, e in events.items() if e.get("attribute_PrimaryArtForm") == "Cinema"}
        upcoming = [i for i in instances if i["event"]["id"] in cinema_events]

        web, checked_events = self._fetch_web_info(client, upcoming)

        showings = []
        dropped = set()
        for inst in upcoming:
            event = cinema_events[inst["event"]["id"]]
            info, sold_out = web.match(inst, event["name"])
            if info is None:
                # Use web info from another performance of the same event, if any.
                info = next((web.match(o, event["name"])[0] for o in upcoming
                             if o["event"]["id"] == event["id"] and web.match(o, event["name"])[0]), None)
            if info is None and event["id"] in checked_events:
                # We read a day this event plays and the public site didn't list it.
                dropped.add(event["name"].strip())
                continue
            showings.append(_to_showing(inst, event, info, sold_out))

        if dropped:
            self._notes.append(f"dropped events not listed on the public site: {sorted(dropped)}")
        return sorted(showings, key=lambda s: (s.start, s.title))

    def source_info(self) -> dict:
        info = super().source_info()
        if self._notes:
            info["notes"] = self._notes
        return info

    def _fetch_web_info(self, client: PoliteClient, upcoming: list[dict]) -> tuple[_WebIndex, set[str]]:
        """Fetch as few day pages as needed for every event to be seen at least once.

        Returns (web info index, ids of events whose day page we read).
        """
        days_by_event: dict[str, set[date]] = {}
        for inst in upcoming:
            days_by_event.setdefault(inst["event"]["id"], set()).add(date.fromisoformat(inst["start"][:10]))

        # Greedy set cover: repeatedly take the day that covers the most unseen events.
        web = _WebIndex()
        checked_events: set[str] = set()
        remaining = set(days_by_event)
        failed_days: set[date] = set()
        pages = 0
        while remaining and pages < MAX_DAY_PAGES:
            counts: dict[date, int] = {}
            for ev in remaining:
                for d in days_by_event[ev] - failed_days:
                    counts[d] = counts.get(d, 0) + 1
            if not counts:
                break
            day = min(counts, key=lambda d: (-counts[d], d))
            covered = {ev for ev in remaining if day in days_by_event[ev]}
            remaining -= covered
            pages += 1
            try:
                html = client.get(DAY_LISTING_URL.format(day=day.isoformat())).text
            except FetchError as e:
                self._notes.append(f"couldn't read day listing {day}: {e}")
                failed_days.add(day)
                remaining |= covered  # try those events on another day
                continue
            by_number, by_time = parse_day_listing(html)
            if not by_number and not by_time:
                self._notes.append(f"day listing {day} had no parsable cards")
                failed_days.add(day)
                remaining |= covered
                continue
            web.add(day, by_number, by_time)
            checked_events |= covered
        if remaining:
            self._notes.append(f"{len(remaining)} events not checked against the website (page cap)")
        return web, checked_events


class _WebIndex:
    """Web info from the day pages we read, looked up per Spektrix instance."""

    def __init__(self):
        self.by_number: dict[str, _WebInfo] = {}
        self.by_day_time: dict[tuple[str, str], list[tuple[_WebInfo, bool]]] = {}

    def add(self, day: date, by_number, by_time) -> None:
        self.by_number.update(by_number)
        for hhmm, entries in by_time.items():
            self.by_day_time[(day.isoformat(), hhmm)] = entries

    def match(self, inst: dict, event_name: str) -> tuple[_WebInfo | None, bool]:
        """Returns (info, sold_out)."""
        info = self.by_number.get(_instance_number(inst["id"]))
        if info is not None:
            return info, False
        # Sold-out performances have no booking link, so fall back to the start
        # time, but only when the titles share a word: two events can start at
        # the same minute, and the other one may not be public at all.
        entries = self.by_day_time.get((inst["start"][:10], inst["start"][11:16]), [])
        candidates = [i for i, sold_out in entries if sold_out and _titles_overlap(i.title, event_name)]
        if len(candidates) == 1:
            return candidates[0], True
        return None, False


def _titles_overlap(a: str, b: str) -> bool:
    def words(t):
        return {w for w in re.findall(r"[a-z0-9']+", clean_title(t).lower()) if len(w) >= 4}
    return bool(words(a) & words(b))


def parse_day_listing(html: str) -> tuple[dict[str, _WebInfo], dict[str, list[tuple[_WebInfo, bool]]]]:
    """Parse one /whats-on/cinema?day= page.

    Returns ({Spektrix instance number: info}, {"HH:MM": [(info, sold_out)]}).
    Sold-out performances have no booking link, so they can only be matched by time.
    """
    soup = BeautifulSoup(html, "html.parser")
    by_number: dict[str, _WebInfo] = {}
    by_time: dict[str, list[tuple[_WebInfo, bool]]] = {}
    for card in soup.select("div.cinema-listing-card"):
        link = card.select_one(".cinema-listing-card__title a")
        if link is None:
            continue
        img = card.select_one(".cinema-listing-card__media img")
        runtime = None
        for tag in card.select(".cinema-listing-card__tag"):
            runtime = runtime or _parse_runtime(tag.get_text(" ", strip=True))
        info = _WebInfo(
            title=link.get_text(strip=True),
            page_url=urljoin(SITE, link["href"]) if link.get("href") else None,
            image_url=urljoin(SITE, img["src"]) if img and img.get("src") else None,
            runtime_minutes=runtime,
        )
        for a in card.select(".cinema-instance-list__instance a"):
            m = _CHOOSE_SEATS.search(a.get("href", ""))
            if m:
                by_number[m.group(1)] = info
            text = a.get_text(" ", strip=True)
            t = _SHOW_TIME.search(text)
            if t:
                by_time.setdefault(_hhmm(t), []).append((info, "sold out" in text.lower()))
    return by_number, by_time


def _hhmm(m: re.Match) -> str:
    hour, minute, ampm = int(m.group(1)), int(m.group(2)), m.group(3).lower()
    hour = hour % 12 + (12 if ampm == "pm" else 0)
    return f"{hour:02d}:{minute:02d}"


def _to_showing(inst: dict, event: dict, info: _WebInfo | None, sold_out: bool) -> Showing:
    start = _utc(inst["startUtc"])
    name = event["name"]
    tags = []
    event_type = event.get("attribute_EventType") or ""
    if event_type and event_type != "Screening - Film":
        tags.append(_EVENT_TYPE_TAGS.get(event_type, _kebab(event_type)))
    for attr, tag in _INSTANCE_FLAG_TAGS.items():
        if inst.get(attr):
            tags.append(tag)
    if re.search(r"\(AD\)", name) and "audio-described" not in tags:
        tags.append("audio-described")
    cert = (event.get("attribute_FilmCertificate") or "").strip()
    if cert:
        tags.append(f"cert:{cert}")
    if event.get("attribute_Season"):
        tags.append(f"season:{event['attribute_Season']}")
    if sold_out:
        tags.append("sold-out")

    return Showing(
        id=f"barbican-cinema:{inst['id']}",
        venue=BarbicanCinema.name,
        category="film",
        # The website's title is the public one, e.g. "Doc'n Roll Film Festival:
        # Amadou & Mariam + ScreenTalk" vs Spektrix's "Amadou & Mariam: ... (15*)".
        title=info.title if info else clean_title(name),
        start=london_iso(start),
        runtime_minutes=info.runtime_minutes if info else None,
        booking_url=BOOKING_URL.format(n=_instance_number(inst["id"])),
        image_url=info.image_url if info else None,
        tags=list(dict.fromkeys(tags)),
    )


def clean_title(name: str) -> str:
    return re.sub(r"\s{2,}", " ", _NAME_NOISE.sub("", name)).strip()



def _parse_runtime(text: str) -> int | None:
    m = _RUNTIME.match(text.strip())
    if not m or not (m.group(1) or m.group(2)):
        return None
    return int(m.group(1) or 0) * 60 + int(m.group(2) or 0)




def _kebab(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


VENUE = BarbicanCinema()
