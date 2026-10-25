"""The output data model and its JSON Schema."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

import jsonschema

from listings.text import match_key

LONDON = ZoneInfo("Europe/London")


CATEGORIES = ("film", "music", "theatre", "comedy", "dance")


@dataclass
class Showing:
    id: str
    venue: str
    category: str  # one of CATEGORIES
    title: str
    start: str  # ISO 8601 with Europe/London offset, e.g. 2026-10-24T18:10:00+01:00
    runtime_minutes: int | None
    booking_url: str | None
    image_url: str | None
    tags: list[str] = field(default_factory=list)
    lineup: list[str] = field(default_factory=list)  # performers, headliner first; empty for films
    doors: str | None = None  # same format as start
    price: str | None = None  # free text, e.g. "From £16"
    genre: str | None = None
    match_key: str = ""  # normalised title for grouping the same film across venues; filled in if empty
    kind: str = "performance"  # "performance", or "run" (a production's run with dates but no times)
    end: str | None = None  # runs only: last date, YYYY-MM-DD

    def to_dict(self) -> dict:
        d = asdict(self)
        d["match_key"] = d["match_key"] or match_key(d["title"])
        return {k: d[k] for k in _FIELD_ORDER}


_FIELD_ORDER = (
    "id", "venue", "category", "kind", "title", "match_key", "start", "end", "doors", "runtime_minutes",
    "lineup", "genre", "price", "booking_url", "image_url", "tags",
)


def upgrade_showing(d: dict) -> dict:
    """Fill in fields added since an older listings.json was written.

    Before these fields existed, every venue was a cinema, so category is "film".
    """
    defaults = {"category": "film", "lineup": [], "doors": None, "price": None, "genre": None,
                "kind": "performance", "end": None}
    out = {k: d.get(k, defaults.get(k)) for k in _FIELD_ORDER}
    out["match_key"] = out.get("match_key") or match_key(out["title"])
    return out


def london_iso(dt: datetime) -> str:
    """Render an aware datetime as ISO 8601 in Europe/London local time."""
    if dt.tzinfo is None:
        raise ValueError("naive datetime; attach a timezone before converting")
    return dt.astimezone(LONDON).isoformat(timespec="seconds")


# ISO 8601 date-time with an explicit offset; London is always +00:00 or +01:00.
_ISO_LONDON = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+0[01]:00$"

LISTINGS_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["generated_at", "showings"],
    "additionalProperties": False,
    "properties": {
        "generated_at": {"type": "string", "pattern": _ISO_LONDON},
        # Extra provenance fields (where the data came from, licence credit).
        "sources": {"type": "array", "items": {"type": "object"}},
        "showings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "id", "venue", "category", "kind", "title", "match_key", "start", "end", "doors",
                    "runtime_minutes", "lineup", "genre", "price",
                    "booking_url", "image_url", "tags",
                ],
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "venue": {"type": "string", "minLength": 1},
                    "category": {"enum": list(CATEGORIES)},
                    "kind": {"enum": ["performance", "run"]},
                    "end": {"type": ["string", "null"], "pattern": r"^\d{4}-\d{2}-\d{2}$"},
                    "lineup": {
                        "type": "array",
                        "items": {"type": "string", "minLength": 1},
                    },
                    "doors": {"type": ["string", "null"], "pattern": _ISO_LONDON},
                    "price": {"type": ["string", "null"], "minLength": 1},
                    "genre": {"type": ["string", "null"], "minLength": 1},
                    "title": {"type": "string", "minLength": 1},
                    "match_key": {"type": "string", "minLength": 1},
                    "start": {"type": "string", "pattern": _ISO_LONDON},
                    "runtime_minutes": {"type": ["integer", "null"], "minimum": 1},
                    "booking_url": {"type": ["string", "null"], "pattern": "^https?://"},
                    "image_url": {"type": ["string", "null"], "pattern": "^https?://"},
                    "tags": {"type": "array", "items": {"type": "string"}, "uniqueItems": True},
                },
                "allOf": [
                    # Films have no lineup.
                    {"if": {"properties": {"category": {"const": "film"}}},
                     "then": {"properties": {"lineup": {"maxItems": 0}}}},
                    # Runs have an end date; performances don't.
                    {"if": {"properties": {"kind": {"const": "run"}}},
                     "then": {"properties": {"end": {"type": "string"}}},
                     "else": {"properties": {"end": {"type": "null"}}}},
                ],
            },
        },
    },
}


def validate_listings(doc: dict) -> None:
    """Raise jsonschema.ValidationError if doc doesn't match the schema."""
    jsonschema.validate(doc, LISTINGS_SCHEMA)
    ids = [s["id"] for s in doc["showings"]]
    if len(ids) != len(set(ids)):
        raise jsonschema.ValidationError("showing ids are not unique")
    for s in doc["showings"]:
        if s["doors"] and datetime.fromisoformat(s["doors"]) > datetime.fromisoformat(s["start"]):
            raise jsonschema.ValidationError(f"{s['id']}: doors is after start")
        if s["end"] and s["end"] < s["start"][:10]:
            raise jsonschema.ValidationError(f"{s['id']}: end is before start")


def is_upcoming(s: dict, now: datetime) -> bool:
    """Performances: not started yet. Runs: not finished yet (end date today or later)."""
    if s.get("kind") == "run" and s.get("end"):
        return s["end"] >= now.astimezone(LONDON).date().isoformat()
    return datetime.fromisoformat(s["start"]) >= now
