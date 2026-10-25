"""Listings from a venue's Spektrix ticketing system.

Spektrix exposes a public, read-only JSON API per venue (the venue's own site
calls it from the browser):

    <api_base>/api/v3/events                    every event, with attribute_* fields
    <api_base>/api/v3/instances?startFrom=DATE  every performance from DATE

Two requests cover the whole programme. Venues set up their own attribute_*
fields, so each venue subclass decides which events are film or music.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

from listings.http import PoliteClient
from listings.model import LONDON, Showing, london_iso
from listings.text import guess_lineup, match_key, tidy_title
from listings.venues.base import Venue

# Spektrix test events that venues forget to hide, e.g. "Test Event - £0.01", "Georgia's Test Screen".
_TEST_EVENT = re.compile(r"\btest\b", re.I)
# Things sold through Spektrix that aren't performances.
NOT_A_SHOW = re.compile(
    r"touch tour|backstage tour|guided tour|architecture tour|ghost tour|\bbuilding tour|pre-?order|"
    r"\bprogramme\b|bundle|captioning facilities|parking|wheelchair|voucher|membership|donation|"
    r"workshop|masterclass|\bclass(?:es)?\b|\bcourse\b|seminar|\bzoom\b|writers'? card|"
    r"^\s*\*\*|reporting|champagne|dinner|\bdrinks\b|kathi roll|yoga|cast album|"
    r"grotto|soft play|secure my booking|name a seat|bootcamp|\bintensive\b|pre[- ]show talk",
    re.I,
)


def fetch_spektrix(client: PoliteClient, api_base: str, start_from: date) -> tuple[dict[str, dict], list[dict]]:
    """Return ({event id: event}, upcoming non-cancelled instances)."""
    events, _ = client.get_json(f"{api_base}/api/v3/events")
    instances, _ = client.get_json(f"{api_base}/api/v3/instances?startFrom={start_from.isoformat()}")
    now = datetime.now(timezone.utc)
    upcoming = [i for i in instances if not i.get("cancelled") and spektrix_utc(i["startUtc"]) >= now]
    return {e["id"]: e for e in events}, upcoming


def spektrix_utc(s: str) -> datetime:
    return datetime.fromisoformat(s.removesuffix("Z")).replace(tzinfo=timezone.utc)


def instance_number(spektrix_id: str) -> str:
    """Spektrix ids look like "3791601AVKCB..."; booking pages use the leading digits."""
    m = re.match(r"\d+", spektrix_id)
    return m.group(0) if m else spektrix_id


def parse_doors(text: str | None, start: datetime) -> str | None:
    """Turn a free-text doors time ("19:00", "7pm", "7:30pm", "5:00") into an ISO
    datetime on the start's date. Returns None unless it's within 3 hours before start."""
    if not text:
        return None
    m = re.search(r"(\d{1,2})(?:[:.](\d{2}))?\s*(am|pm)?", text.strip(), re.I)
    if not m:
        return None
    hour, minute, ampm = int(m.group(1)), int(m.group(2) or 0), (m.group(3) or "").lower()
    if ampm == "pm" and hour < 12:
        hour += 12
    elif not ampm and hour < 12 and start.astimezone(LONDON).hour >= 12:
        hour += 12  # "5:00" before an evening show means 17:00
    if hour > 23 or minute > 59:
        return None
    local_start = start.astimezone(LONDON)
    doors = local_start.replace(hour=hour, minute=minute, second=0)
    if not (local_start - timedelta(hours=3) <= doors <= local_start):
        return None
    return london_iso(doors)


def load_title_links(client: PoliteClient, page_url: str, link_pattern: str) -> dict[str, str]:
    """{match_key(link text): absolute URL} for event links on a listing page. Errors -> {}."""
    from urllib.parse import urljoin, urlsplit

    from bs4 import BeautifulSoup

    from listings.http import FetchError

    try:
        resp = client.get(page_url)
    except FetchError:
        return {}
    host = urlsplit(resp.url).netloc.removeprefix("www.")
    links: dict[str, str] = {}
    for a in BeautifulSoup(resp.text, "html.parser").find_all("a", href=True):
        href = urljoin(resp.url, a["href"]).split("#")[0]
        text = a.get_text(" ", strip=True)
        if (urlsplit(href).netloc.removeprefix("www.") == host and re.search(link_pattern, href)
                and len(text) > 2 and text.lower() not in ("book now", "more info", "find out more", "details", "read more")):
            links.setdefault(match_key(text), href)
    return links


def match_title_to_url(title: str, links: dict[str, str]) -> str | None:
    """Exact normalised-title match, else a single unambiguous containment match."""
    if not links:
        return None
    key = match_key(title)
    if key in links:
        return links[key]
    if len(key) < 6:
        return None
    hits = {url for k, url in links.items() if len(k) >= 6 and (key in k or k in key)}
    return hits.pop() if len(hits) == 1 else None


class SpektrixVenue(Venue):
    """A venue whose listings come straight from its Spektrix API."""

    #: e.g. "https://buy.ica.art/ica" (the part before /api/v3).
    api_base: str
    #: Category for events no rule matches (None = leave them out).
    default_category: str | None = None
    #: Ordered (field, regex, category) rules; the first match decides, and a
    #: category of None leaves the event out. `field` is an event attribute
    #: ("attribute_Genre"), "name", or "instance.<attribute>" for performance attributes.
    rules: tuple = ()
    #: Set for venues that are sometimes between seasons with nothing on sale,
    #: so an empty programme isn't reported as a failure.
    allow_empty: bool = False
    #: Ignore performances further ahead than this (placeholders such as 2099-12-31).
    horizon_days: int = 730
    #: The venue's what's-on page. Spektrix rarely has a web URL per event, so
    #: info_url comes from links on this page, matched by title (one request).
    info_page: str | None = None
    info_link_pattern: str = r"/(?:whats-on|events?|productions?|shows?|films?|performances?)/[^/?#]+"

    _info_links: dict = {}

    @property
    def source_description(self) -> str:
        return f"Spektrix ticketing API ({self.api_base}/api/v3)"

    # -- hooks for subclasses ------------------------------------------------

    def category(self, event: dict, instance: dict) -> str | None:
        """A category from listings.model.CATEGORIES, or None to leave the event out.

        Default: apply `rules`, then `default_category`. Subclasses may override."""
        if NOT_A_SHOW.search(event.get("name", "")):
            return None
        for field, pattern, category in self.rules:
            if field == "name":
                value = event.get("name", "")
            elif field.startswith("instance."):
                value = instance.get(field.removeprefix("instance."))
            else:
                value = event.get(field)
            if value is not None and re.search(pattern, str(value), re.I):
                return category
        return self.default_category

    def details(self, event: dict, instance: dict, category: str) -> dict:
        """Extra Showing fields (tags, genre, doors, lineup...). Override as needed.

        Default: guess a lineup for music and comedy from the title."""
        if category in ("music", "comedy"):
            return {"lineup": guess_lineup(event["name"])}
        return {}

    def info_url(self, event: dict) -> str | None:
        """The event's public page: Spektrix webUrl if set, else a title match on info_page."""
        if event.get("webUrl"):
            return event["webUrl"]
        return match_title_to_url(event["name"], self._info_links)

    def booking_url(self, instance: dict) -> str:
        return f"{self.api_base}/website/ChooseSeats.aspx?EventInstanceId={instance_number(instance['id'])}"

    # -- shared logic -------------------------------------------------------

    def fetch(self, client: PoliteClient) -> list[Showing]:
        self._info_links = load_title_links(client, self.info_page, self.info_link_pattern) if self.info_page else {}
        events, instances = fetch_spektrix(client, self.api_base, datetime.now(LONDON).date())
        showings = []
        for inst in instances:
            event = events.get(inst["event"]["id"])
            if event is None or _TEST_EVENT.search(event["name"]):
                continue
            category = self.category(event, inst)
            if category is None:
                continue
            start = spektrix_utc(inst["startUtc"])
            if start > datetime.now(timezone.utc) + timedelta(days=self.horizon_days):
                continue
            fields = {
                "runtime_minutes": (event.get("duration") or None) if category != "music" else None,
                "image_url": event.get("imageUrl") or None,
                "tags": [],
            }
            fields.update(self.details(event, inst, category))
            showings.append(Showing(
                id=f"{self.slug}:{inst['id']}",
                venue=self.name,
                category=category,
                title=tidy_title(event["name"]),
                start=london_iso(start),
                booking_url=self.booking_url(inst),
                info_url=self.info_url(event),
                description=event.get("htmlDescription") or event.get("description"),
                **fields,
            ))
        if not showings and not self.allow_empty:
            raise ValueError("Spektrix returned no performances in the categories we keep")
        return sorted(showings, key=lambda s: (s.start, s.title))
