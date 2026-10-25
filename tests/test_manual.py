"""Offline tests for hand-entered listings in manual/."""

import json
from datetime import datetime, timedelta

import pytest

import listings.__main__ as cli
from listings.manual import load_manual
from listings.model import LONDON, Showing, london_iso, validate_listings
from listings.venues.base import Venue

NOW = datetime.now(LONDON).replace(second=0, microsecond=0)


def _at(hours):
    return (NOW + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M")


def _write(tmp_path, name, data):
    (tmp_path / name).write_text(json.dumps(data))


class FakeVenue(Venue):
    def __init__(self, slug, name, showings=(), error=None):
        self.slug, self.name, self.source_description = slug, name, f"fake {slug}"
        self._showings, self._error = list(showings), error

    def fetch(self, client):
        if self._error:
            raise self._error
        return self._showings


@pytest.fixture
def venues(monkeypatch):
    registry = {}
    monkeypatch.setattr(cli, "all_venues", lambda: registry)
    return registry


def test_loads_fills_defaults_and_drops_past(tmp_path):
    _write(tmp_path, "20261101_lamb.json", {
        "venue": "Slaughtered Lamb", "category": "music",
        "showings": [
            {"title": "Gone", "start": _at(-5)},
            {"title": "Coming Up", "start": _at(30), "doors": "00:00", "lineup": ["Coming Up"], "price": "£10"},
        ],
    })
    venues, errors = load_manual(tmp_path)
    assert errors == []
    (v,) = venues
    assert v.slug == "slaughtered-lamb" and v.skipped_past == 1
    (s,) = v.showings
    assert s["id"].startswith("slaughtered-lamb:manual-")
    assert s["category"] == "music" and s["lineup"] == ["Coming Up"] and "manual" in s["tags"]
    assert s["start"].endswith(("+00:00", "+01:00"))  # London offset added
    validate_listings({"generated_at": london_iso(NOW), "showings": v.showings})


def test_doors_after_start_rejects_the_file_with_a_clear_error(tmp_path):
    start = (NOW + timedelta(days=2)).replace(hour=20, minute=0)
    _write(tmp_path, "x.json", {"venue": "X", "category": "music",
                                "showings": [{"title": "T", "start": start.strftime("%Y-%m-%dT%H:%M"), "doors": "21:00"}]})
    venues, errors = load_manual(tmp_path)
    assert venues == [] and len(errors) == 1 and "doors is after start" in errors[0]


def test_bad_files_are_reported_and_skipped(tmp_path):
    (tmp_path / "broken.json").write_text("{not json")
    _write(tmp_path, "no_title.json", {"venue": "Y", "showings": [{"start": _at(5)}]})
    _write(tmp_path, "good.json", {"venue": "Z", "showings": [{"title": "Fine", "start": _at(5)}]})
    _write(tmp_path, "20261024_example.json", {"venue": "Ignored", "showings": [{"title": "x", "start": _at(5)}]})
    venues, errors = load_manual(tmp_path)
    assert [v.slug for v in venues] == ["z"]
    assert len(errors) == 2


def test_manual_merges_with_scraped_and_scraped_wins(tmp_path, venues):
    start = NOW + timedelta(days=2)
    scraped = Showing(id="lamb:1", venue="The Slaughtered Lamb", category="music", title="Same Show",
                      start=london_iso(start), runtime_minutes=None, booking_url="https://example.com/a",
                      image_url=None)
    venues["lamb"] = FakeVenue("lamb", "The Slaughtered Lamb", [scraped])
    _write(tmp_path, "lamb.json", {
        "venue": "Slaughtered Lamb (typo)", "venue_slug": "lamb", "category": "music",
        "showings": [
            {"title": "Same Show", "start": start.strftime("%Y-%m-%dT%H:%M")},   # duplicate of scraped
            {"title": "Missed By Scraper", "start": _at(72)},
        ],
    })
    doc, errors = cli.collect(None, client=object(), manual_dir=tmp_path)
    assert errors == []
    titles = [(s["title"], s["id"]) for s in doc["showings"]]
    assert ("Same Show", "lamb:1") in titles                      # scraped kept
    assert sum(t == "Same Show" for t, _ in titles) == 1          # manual duplicate dropped
    assert any(t == "Missed By Scraper" for t, _ in titles)
    assert {s["venue"] for s in doc["showings"]} == {"The Slaughtered Lamb"}  # scraper's name wins
    assert any(s["status"] == "manual" for s in doc["sources"])


def test_failed_venue_does_not_carry_over_old_manual_entries(tmp_path, venues):
    venues["lamb"] = FakeVenue("lamb", "The Slaughtered Lamb", error=RuntimeError("down"))
    previous = {"showings": [
        {"id": "lamb:manual-abc", "venue": "The Slaughtered Lamb", "category": "music", "title": "Deleted By Hand",
         "start": london_iso(NOW + timedelta(days=3)), "doors": None, "runtime_minutes": None, "lineup": [],
         "genre": None, "price": None, "booking_url": None, "image_url": None, "tags": ["manual"]},
    ]}
    doc, errors = cli.collect(None, client=object(), previous=previous, manual_dir=tmp_path)
    assert [s["title"] for s in doc["showings"]] == []


def test_manual_run_entry_kept_until_end(tmp_path):
    _write(tmp_path, "nt.json", {"venue": "National Theatre", "category": "theatre", "showings": [
        {"title": "Running Now", "kind": "run", "start": (NOW - timedelta(days=30)).strftime("%Y-%m-%d"),
         "end": (NOW + timedelta(days=30)).strftime("%Y-%m-%d")},
        {"title": "Finished", "kind": "run", "start": (NOW - timedelta(days=60)).strftime("%Y-%m-%d"),
         "end": (NOW - timedelta(days=1)).strftime("%Y-%m-%d")},
    ]})
    venues, errors = load_manual(tmp_path)
    assert errors == []
    assert [s["title"] for s in venues[0].showings] == ["Running Now"]
    assert venues[0].skipped_past == 1
