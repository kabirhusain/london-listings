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
        "id", "venue", "category", "kind", "title", "match_key", "start", "end", "doors", "runtime_minutes",
        "lineup", "genre", "price", "booking_url", "info_url", "image_url", "tags",
    ]


@pytest.mark.parametrize("field, value", [
    ("category", "opera"),          # only film/music/theatre/comedy/dance
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


@pytest.mark.parametrize("field", ["category", "lineup", "doors", "price", "genre", "match_key", "kind", "end"])
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
    old = {k: v for k, v in FILM.items() if k not in ("category", "lineup", "doors", "price", "genre", "match_key", "kind", "end")}
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


@pytest.mark.parametrize("title, key", [
    ("Shaun of the Dead", "shaun of the dead"),
    ("The Rocky Horror Picture Show Sing Along", "rocky horror picture show"),
    ("Road House", "road house"),
    ("Full Steam Ahead", "full steam ahead"),
    ("Possible Love (AD)", "possible love"),
    ("Wild Horse Nine - 35mm", "wild horse nine"),
])
def test_match_key_strips_whole_format_words_only(title, key):
    from listings.text import match_key
    assert match_key(title) == key


@pytest.mark.parametrize("a, b", [
    ("Dune: Part Two", "Dune"),
    ("2001: A Space Odyssey", "A Space Odyssey"),
    ("Blade Runner (Director's Cut)", "Blade Runner"),
])
def test_match_key_keeps_distinct_titles_apart(a, b):
    from listings.text import match_key
    assert match_key(a) != match_key(b)


@pytest.mark.parametrize("category", ["theatre", "comedy", "dance"])
def test_new_categories_are_valid(category):
    validate_listings(_doc(dict(GIG, category=category)))


RUN = Showing(
    id="v:3", venue="Venue", category="theatre", kind="run", title="A Play",
    start="2026-11-10T00:00:00+00:00", end="2027-01-09", runtime_minutes=None,
    booking_url=None, image_url=None,
).to_dict()


def test_run_is_valid():
    validate_listings(_doc(RUN))


@pytest.mark.parametrize("bad", [
    {"end": None},                      # runs need an end date
    {"end": "2026-11-01"},              # end before start
    {"end": "9 Jan 2027"},              # YYYY-MM-DD only
    {"kind": "season"},
])
def test_bad_runs_are_rejected(bad):
    with pytest.raises(ValidationError):
        validate_listings(_doc(dict(RUN, **bad)))


def test_performance_cannot_have_end():
    with pytest.raises(ValidationError):
        validate_listings(_doc(dict(FILM, end="2026-12-01")))


def test_run_is_upcoming_until_its_end_date():
    from datetime import datetime
    from listings.model import LONDON, is_upcoming
    started = dict(RUN, start="2026-09-08T00:00:00+01:00", end="2026-10-31")
    assert is_upcoming(started, datetime(2026, 10, 25, 12, tzinfo=LONDON))
    assert not is_upcoming(started, datetime(2026, 11, 1, 12, tzinfo=LONDON))


@pytest.mark.parametrize("text, expected", [
    ("Tue 10 Nov – Wed 23 Dec 2026", ("2026-11-10", "2026-12-23")),
    ("10 Nov 2026–09 Jan 2027", ("2026-11-10", "2027-01-09")),
    ("01–31 Oct 2026", ("2026-10-01", "2026-10-31")),
    ("19 Dec 2026", ("2026-12-19", "2026-12-19")),
    ("Sat 21 Nov - Sat 17 Apr 2027", ("2026-11-21", "2027-04-17")),
    ("Jun - Jul 2027", None),
    ("Early 2028", None),
])
def test_parse_date_range(text, expected):
    from listings.text import parse_date_range
    got = parse_date_range(text)
    assert (tuple(d.isoformat() for d in got) if got else None) == expected


def test_make_blurb_cleans_and_trims():
    from listings.text import BLURB_MAX, make_blurb
    raw = ("<p><strong>ALL NIGHTER: HOUSE RULES</strong><br/>Please note: the bar closes at 2am.<br/>"
           "A drifter arrives in a small town and nothing is the same again. " * 6 + "<br/>Tickets £12</p>")
    b = make_blurb(raw)
    assert b and len(b) <= BLURB_MAX and b.endswith(".")
    assert "£" not in b and "bar closes" not in b and "HOUSE RULES" not in b
    assert make_blurb("Reverend Baron at Bush Hall at 2026-11-18T19:00:00+0000") is None
    assert make_blurb("Short.") is None


def test_one_blurb_per_title_best_wins_and_previous_kept():
    from listings.__main__ import pick_blurbs
    showings = [dict(FILM, match_key="wild horse nine"), dict(FILM, id="v:9", match_key="other film")]
    candidates = {"film:wild horse nine": ["Short one.", "A much better, longer description of the film that reads well."]}
    out = pick_blurbs(showings, candidates, previous={"film:other film": "Kept from yesterday.", "film:gone": "x"})
    assert out == {"film:wild horse nine": "A much better, longer description of the film that reads well.",
                   "film:other film": "Kept from yesterday."}


def test_info_url_is_optional_and_validated():
    validate_listings(_doc(dict(GIG, info_url="https://www.example.com/whats-on/show")))
    validate_listings(_doc(dict(GIG, info_url=None)))
    old = {k: v for k, v in GIG.items() if k != "info_url"}       # written before info_url existed
    validate_listings(_doc(old))
    for bad in ("www.example.com/show", "/whats-on/show", "", 42):
        with pytest.raises(ValidationError):
            validate_listings(_doc(dict(GIG, info_url=bad)))


def test_info_url_sits_next_to_booking_url_which_is_unchanged():
    keys = list(GIG)
    assert keys.index("info_url") == keys.index("booking_url") + 1
    assert GIG["booking_url"] == "https://example.com/b" and GIG["info_url"] is None


def test_upgrade_keeps_info_url_missing_as_null():
    from listings.model import upgrade_showing
    old = {k: v for k, v in GIG.items() if k != "info_url"}
    assert upgrade_showing(old)["info_url"] is None
    assert upgrade_showing(dict(GIG, info_url="https://x.org/e"))["info_url"] == "https://x.org/e"
