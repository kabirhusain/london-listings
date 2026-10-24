"""Offline tests for merging venues and falling back to last good data."""

from datetime import datetime, timedelta, timezone

import pytest

import listings.__main__ as cli
from listings.model import Showing, london_iso, validate_listings
from listings.venues.base import Venue

NOW = datetime.now(timezone.utc)


def _showing(slug, venue, title, hours_from_now, n=0):
    return Showing(
        id=f"{slug}:{n}",
        venue=venue,
        category="film",
        title=title,
        start=london_iso(NOW + timedelta(hours=hours_from_now)),
        runtime_minutes=90,
        booking_url="https://example.com/book",
        image_url=None,
        tags=[],
    )


def _old_schema(d):
    """A showing as written before category/lineup/doors/price/genre existed."""
    return {k: v for k, v in d.items() if k not in ("category", "lineup", "doors", "price", "genre")}


class FakeVenue(Venue):
    def __init__(self, slug, name, showings=None, error=None):
        self.slug, self.name, self.source_description = slug, name, f"fake {slug}"
        self._showings, self._error = showings or [], error

    def fetch(self, client):
        if self._error:
            raise self._error
        return self._showings


@pytest.fixture
def venues(monkeypatch):
    registry = {}
    monkeypatch.setattr(cli, "all_venues", lambda: registry)
    return registry


def test_merge_sorts_by_start_and_dedupes(venues):
    venues["a"] = FakeVenue("a", "Venue A", [
        _showing("a", "Venue A", "Late", 5, n=1),
        _showing("a", "Venue A", "Early", 1, n=2),
        _showing("a", "Venue A", "early", 1, n=3),  # same venue/title/start, different id
    ])
    venues["b"] = FakeVenue("b", "Venue B", [_showing("b", "Venue B", "Middle", 3)])

    doc, errors = cli.collect(None, client=object())
    assert errors == []
    assert [s["title"] for s in doc["showings"]] == ["Early", "Middle", "Late"]
    validate_listings(doc)


def test_failed_venue_keeps_last_good_upcoming_data(venues):
    venues["a"] = FakeVenue("a", "Venue A", [_showing("a", "Venue A", "Fresh", 2)])
    venues["b"] = FakeVenue("b", "Venue B", error=RuntimeError("site down"))
    previous = {
        "generated_at": london_iso(NOW - timedelta(days=1)),
        "sources": [{"venue": "b", "status": "ok", "fetched_at": "2026-01-01T06:00:00+00:00",
                     "source": "fake b", "showings": 2}],
        "showings": [
            _showing("b", "Venue B", "Already happened", -3, n=1).to_dict(),
            _old_schema(_showing("b", "Venue B", "Still to come", 4, n=2).to_dict()),
            _showing("a", "Venue A", "Old A data", 4, n=9).to_dict(),  # A succeeded: not reused
        ],
    }

    doc, errors = cli.collect(None, client=object(), previous=previous)

    assert len(errors) == 1 and "site down" in errors[0]
    assert [s["title"] for s in doc["showings"]] == ["Fresh", "Still to come"]
    b = next(s for s in doc["sources"] if s["venue"] == "b")
    assert b["status"] == "stale"
    assert b["fetched_at"] == "2026-01-01T06:00:00+00:00"  # when the data was really fetched
    carried = doc["showings"][1]
    assert carried["category"] == "film" and carried["lineup"] == []  # upgraded from old schema
    validate_listings(doc)


def test_failed_venue_without_previous_data_is_marked_failed(venues):
    venues["a"] = FakeVenue("a", "Venue A", [_showing("a", "Venue A", "Fresh", 2)])
    venues["b"] = FakeVenue("b", "Venue B", error=RuntimeError("site down"))

    doc, errors = cli.collect(None, client=object())

    assert [s["title"] for s in doc["showings"]] == ["Fresh"]
    assert next(s for s in doc["sources"] if s["venue"] == "b")["status"] == "failed"


def test_failed_venue_prefers_fresher_local_run(venues):
    venues["b"] = FakeVenue("b", "Venue B", error=RuntimeError("403 from GitHub's IPs"))
    old = {"sources": [{"venue": "b", "status": "ok", "fetched_at": "2026-01-01T06:00:00+00:00"}],
           "showings": [_showing("b", "Venue B", "From old CI run", 4, n=1).to_dict()]}
    local = {"sources": [{"venue": "b", "status": "ok", "fetched_at": "2026-01-02T05:30:00+00:00"}],
             "showings": [_showing("b", "Venue B", "From local run", 4, n=2).to_dict()]}
    doc, _ = cli.collect(None, client=object(), previous=old, local=[local])
    assert [s["title"] for s in doc["showings"]] == ["From local run"]
    assert doc["sources"][0]["fetched_at"] == "2026-01-02T05:30:00+00:00"


def test_status_tracks_last_success_across_failures(venues):
    venues["a"] = FakeVenue("a", "Venue A", [_showing("a", "Venue A", "Fresh", 2)])
    venues["b"] = FakeVenue("b", "Venue B", error=RuntimeError("site down"))
    doc, _ = cli.collect(None, client=object())
    previous_status = {"venues": [{"venue": "b", "last_success": "2026-01-01T06:00:00+00:00"}]}
    status = cli.build_status(doc, previous_status)
    by = {v["venue"]: v for v in status["venues"]}
    assert by["a"]["status"] == "ok" and by["a"]["listings"] == 1 and by["a"]["last_success"] == doc["generated_at"]
    assert by["b"]["status"] == "failed" and by["b"]["last_success"] == "2026-01-01T06:00:00+00:00"
    assert "site down" in by["b"]["error"]
    assert status["summary"] == {"ok": 1, "stale": 0, "failed": 1, "manual": 0}
