"""Offline tests for the listings.json schema."""

import copy

import pytest
from jsonschema import ValidationError

from listings.model import Showing, upgrade_showing, validate_listings

FILM = Showing(
    id="v:1", venue="Venue", category="film", title="A Film",
    start="2026-11-01T19:30:00+00:00", runtime_minutes=None,
    booking_url=None, image_url=None,
).to_dict()

GIG = Showing(
    id="v:2", venue="Venue", category="music", title="Headliner + Support",
    start="2026-11-01T20:00:00+00:00", doors="2026-11-01T19:00:00+00:00",
    runtime_minutes=None, lineup=["Headliner", "Support"], genre="Folk",
    price="From £16", booking_url="https://example.com/b", image_url=None,
).to_dict()


def _doc(*showings):
    return {"generated_at": "2026-10-25T06:00:00+00:00", "showings": list(showings)}


def test_film_and_gig_are_valid():
    validate_listings(_doc(FILM, GIG))


def test_every_field_is_present_in_output_order():
    assert list(GIG) == [
        "id", "venue", "category", "title", "match_key", "start", "doors", "runtime_minutes",
        "lineup", "genre", "price", "booking_url", "image_url", "tags",
    ]


@pytest.mark.parametrize("field, value", [
    ("category", "theatre"),        # only film or music
    ("lineup", "Headliner"),         # must be a list
    ("lineup", [""]),                # no empty names
    ("doors", "19:00"),              # full ISO datetime, like start
    ("price", ""),                   # null, not empty string
    ("genre", 3),
    ("runtime_minutes", 0),
])
def test_bad_values_are_rejected(field, value):
    bad = copy.deepcopy(GIG)
    bad[field] = value
    with pytest.raises(ValidationError):
        validate_listings(_doc(bad))


@pytest.mark.parametrize("field", ["category", "lineup", "doors", "price", "genre", "match_key"])
def test_new_fields_are_required(field):
    bad = copy.deepcopy(GIG)
    del bad[field]
    with pytest.raises(ValidationError):
        validate_listings(_doc(bad))


def test_film_with_lineup_is_rejected():
    bad = dict(FILM, lineup=["Someone"])
    with pytest.raises(ValidationError):
        validate_listings(_doc(bad))


def test_doors_after_start_is_rejected():
    bad = dict(GIG, doors="2026-11-01T21:00:00+00:00")
    with pytest.raises(ValidationError):
        validate_listings(_doc(bad))


def test_upgrade_fills_old_schema_showing():
    old = {k: v for k, v in FILM.items() if k not in ("category", "lineup", "doors", "price", "genre", "match_key")}
    assert upgrade_showing(old) == FILM


@pytest.mark.parametrize("a, b", [
    ("Your Name [Kimi no Na wa.]", "YOUR NAME (4K Restoration)"),
    ("Preview: Wild Horse Nine + ScreenTalk", "Wild Horse Nine (2D)"),
    ("Sense & Sensibility (1995)", "Relaxed Screening: Sense and Sensibility"),
    ("Amélie - 25th Anniversary", "Amelie"),
    ("LPFF 2026: Who is Still Alive", "Who Is Still Alive"),
])
def test_match_key_groups_variants(a, b):
    from listings.text import match_key
    assert match_key(a) == match_key(b)


@pytest.mark.parametrize("a, b", [
    ("Dune: Part Two", "Dune"),
    ("2001: A Space Odyssey", "A Space Odyssey"),
    ("Blade Runner (Director's Cut)", "Blade Runner"),
])
def test_match_key_keeps_distinct_titles_apart(a, b):
    from listings.text import match_key
    assert match_key(a) != match_key(b)
