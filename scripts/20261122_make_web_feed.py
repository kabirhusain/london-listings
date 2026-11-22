"""Split listings.json into two smaller files for the website.

    python scripts/20261122_make_web_feed.py site

Reads site/listings.json and writes, without whitespace:

- site/data/soon.json: everything on listing dates D0-1 .. D0+15, where D0 is the
  listing date of generated_at. That is enough to draw Today, This evening and the
  next 14 days, and it keeps the first download small.
- site/data/later.json: everything after that. The site loads it in the background
  for search, the calendar and a title's full list of showtimes.

A listing date follows the apps' 5am rollover: a 00:30 screening belongs to the
evening before. Runs (kind "run") go in soon.json if any of their days fall in
the window. Entries that have already finished are dropped. Each file carries the
blurbs for its own titles; a title in both files has its blurb in soon.json only.

Each source also gets what the website needs to credit it publicly: the venue's
display name, and "via"/"via_url" when its listings come from an aggregator
(Clusterflick, Songkick, DICE). "attribution" (licence credit) is passed through.

listings.json itself is left unchanged (the Android app reads it).
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

LONDON = ZoneInfo("Europe/London")
ROLLOVER_HOUR = 5  # matches DAY_ROLLOVER_HOUR in the Android app and the website
DAYS_BEFORE = 1  # slack for someone looking before 5am, or a feed generated late
DAYS_AFTER = 15  # today + the 14-day Upcoming list, plus one day of slack
SOURCE_FIELDS = ("venue", "status", "attribution")

# Aggregators whose listings we republish, by a marker in the source description.
# The url is where the website's credit links to (the venue's page there when known).
AGGREGATORS = (
    ("clusterflick", "Clusterflick", "https://clusterflick.com"),
    ("songkick.com", "Songkick", "https://www.songkick.com"),
    ("dice.fm", "DICE", "https://dice.fm"),
)
_URL = re.compile(r"https?://[^\s)]+")


def credit_source(src: dict, names: dict[str, str]) -> dict:
    """The fields the website shows for one source: name, status, licence credit, aggregator."""
    out = {k: src[k] for k in SOURCE_FIELDS if k in src}
    out["name"] = names.get(src.get("venue"), src.get("venue"))
    text = src.get("source") or ""
    for marker, label, home in AGGREGATORS:
        if marker in text.lower():
            out["via"] = label
            urls = [u for u in _URL.findall(text) if marker in u and "github.com" not in u]
            out["via_url"] = urls[0] if urls else home
            break
    return out


def london(iso: str) -> datetime:
    return datetime.fromisoformat(iso).astimezone(LONDON)


def listing_date(iso: str) -> date:
    """The listings day a start time belongs to: before 5am counts as the previous day.

    Like the apps, this subtracts 5 hours from the instant, then takes the London date.
    """
    return (datetime.fromisoformat(iso) - timedelta(hours=ROLLOVER_HOUR)).astimezone(LONDON).date()


def run_dates(showing: dict) -> tuple[date, date]:
    """First and last day of a run. A missing or unreadable end means the first day only."""
    first = london(showing["start"]).date()
    last = first
    end = showing.get("end")
    if end:
        try:
            last = date.fromisoformat(end[:10]) if len(end) == 10 else london(end).date()
        except ValueError:
            pass
    return first, max(first, last)


def venue_names(doc: dict, status: dict | None = None) -> dict[str, str]:
    """Venue slug -> display name: from status.json when given, else from showing ids ("<slug>:...")."""
    names = {s["id"].split(":", 1)[0]: s["venue"] for s in doc.get("showings", []) if ":" in s.get("id", "")}
    for v in (status or {}).get("venues", []):
        if v.get("venue") and v.get("name"):
            names[v["venue"]] = v["name"]
    return names


def split(doc: dict, status: dict | None = None) -> tuple[dict, dict]:
    d0 = listing_date(doc["generated_at"])
    lo, hi = d0 - timedelta(days=DAYS_BEFORE), d0 + timedelta(days=DAYS_AFTER)
    soon, later = [], []
    for s in doc.get("showings", []):
        try:
            if s.get("kind") == "run":
                first, last = run_dates(s)
                if last < lo:
                    continue
                (soon if first <= hi else later).append(s)
            else:
                day = listing_date(s["start"])
                if day < lo:
                    continue
                (soon if day <= hi else later).append(s)
        except (KeyError, TypeError, ValueError):
            later.append(s)  # let the site's parser decide what to do with it

    blurbs = doc.get("blurbs") or {}

    def blurbs_for(showings: list[dict], exclude: set[str] = frozenset()) -> dict:
        keys = {f"{s.get('category')}:{s.get('match_key')}" for s in showings}
        return {k: blurbs[k] for k in sorted(keys - exclude) if k in blurbs}

    soon_blurbs = blurbs_for(soon)
    later_blurbs = blurbs_for(later, exclude=set(soon_blurbs))
    names = venue_names(doc, status)
    sources = [credit_source(src, names) for src in doc.get("sources", [])]
    window = {"from": lo.isoformat(), "to": hi.isoformat()}

    def part(name: str, showings: list[dict], part_blurbs: dict) -> dict:
        return {"generated_at": doc["generated_at"], "part": name, "window": window,
                "sources": sources, "blurbs": part_blurbs, "showings": showings}

    return part("soon", soon, soon_blurbs), part("later", later, later_blurbs)


def main(site: Path) -> None:
    doc = json.loads((site / "listings.json").read_text(encoding="utf-8"))
    status_path = site / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else None
    out = site / "data"
    out.mkdir(parents=True, exist_ok=True)
    for piece in split(doc, status):
        path = out / f"{piece['part']}.json"
        path.write_text(json.dumps(piece, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"{path}: {len(piece['showings'])} showings, {len(piece['blurbs'])} blurbs, "
              f"{path.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "site"))
