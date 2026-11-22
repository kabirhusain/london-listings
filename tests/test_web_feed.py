"""Offline tests for scripts/20261122_make_web_feed.py (the website's two-part feed)."""

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "make_web_feed", Path(__file__).resolve().parent.parent / "scripts" / "20261122_make_web_feed.py")
web_feed = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(web_feed)


def show(id, start, category="film", kind="performance", end=None, match_key=None):
    return {"id": id, "venue": "V", "category": category, "kind": kind, "title": id,
            "match_key": match_key or id, "start": start, "end": end, "booking_url": "https://x"}


# Sunday 22 Nov 2026, 06:00 London (GMT): D0 = 22 Nov, window 21 Nov .. 7 Dec.
GENERATED = "2026-11-22T06:00:00+00:00"


def doc(*showings, blurbs=None):
    return {"generated_at": GENERATED, "sources": [
        {"venue": "bfi-southbank", "status": "ok", "attribution": "Clusterflick", "source": "x", "showings": 3},
        {"venue": "old-vic", "status": "stale", "error": "404"},
    ], "blurbs": blurbs or {}, "showings": list(showings)}


def ids(part):
    return [s["id"] for s in part["showings"]]


def test_window_edges():
    soon, later = web_feed.split(doc(
        show("too-old", "2026-11-20T20:00:00+00:00"),
        show("day-before", "2026-11-21T20:00:00+00:00"),
        show("today", "2026-11-22T19:00:00+00:00"),
        show("last-in", "2026-12-07T21:00:00+00:00"),
        # 02:00 on 8 Dec belongs to the evening of 7 Dec (5am rollover).
        show("after-midnight", "2026-12-08T02:00:00+00:00"),
        show("first-out", "2026-12-08T19:00:00+00:00"),
        show("next-year", "2027-03-01T19:00:00+00:00"),
    ))
    assert soon["window"] == {"from": "2026-11-21", "to": "2026-12-07"}
    assert ids(soon) == ["day-before", "today", "last-in", "after-midnight"]
    assert ids(later) == ["first-out", "next-year"]
    assert soon["part"] == "soon" and later["part"] == "later"


def test_rollover_uses_london_time_across_dst():
    # 23:30 UTC on 1 Jul is 00:30 BST on 2 Jul: still the evening of 1 Jul.
    assert str(web_feed.listing_date("2027-07-01T23:30:00+00:00")) == "2027-07-01"
    assert str(web_feed.listing_date("2027-07-02T04:30:00+00:00")) == "2027-07-02"  # 05:30 BST
    assert str(web_feed.listing_date("2026-11-23T04:59:00+00:00")) == "2026-11-22"


def test_runs_go_where_they_overlap():
    soon, later = web_feed.split(doc(
        show("ended", "2026-10-01T00:00:00+01:00", category="theatre", kind="run", end="2026-11-19"),
        show("straddles", "2026-11-10T00:00:00+00:00", category="theatre", kind="run", end="2027-01-09"),
        show("starts-in-window", "2026-12-03T00:00:00+00:00", category="theatre", kind="run", end="2026-12-03"),
        show("starts-later", "2027-01-14T00:00:00+00:00", category="theatre", kind="run", end="2027-03-13"),
        show("no-end", "2026-11-25T00:00:00+00:00", category="theatre", kind="run"),
    ))
    assert ids(soon) == ["straddles", "starts-in-window", "no-end"]
    assert ids(later) == ["starts-later"]


def test_nothing_lost_or_duplicated():
    showings = [show(f"s{i}", f"2026-{11 + i // 40:02d}-{1 + i % 28:02d}T19:00:00+00:00") for i in range(80)]
    soon, later = web_feed.split(doc(*showings))
    both = ids(soon) + ids(later)
    assert len(both) == len(set(both))
    upcoming = {s["id"] for s in showings if web_feed.listing_date(s["start"]) >= web_feed.date(2026, 11, 21)}
    assert set(both) == upcoming


def test_blurbs_follow_their_titles():
    soon, later = web_feed.split(doc(
        show("a", "2026-11-22T19:00:00+00:00", match_key="nosferatu"),
        show("b", "2027-01-22T19:00:00+00:00", match_key="nosferatu"),
        show("c", "2027-01-22T19:00:00+00:00", match_key="la haine"),
        show("d", "2026-11-23T19:00:00+00:00", category="music", match_key="la haine"),
        blurbs={"film:nosferatu": "Vampire.", "film:la haine": "Riots.", "film:unused": "Gone."},
    ))
    assert soon["blurbs"] == {"film:nosferatu": "Vampire."}
    assert later["blurbs"] == {"film:la haine": "Riots."}


def test_sources_keep_only_what_the_site_uses():
    soon, _ = web_feed.split(doc())
    assert soon["sources"] == [
        {"venue": "bfi-southbank", "status": "ok", "attribution": "Clusterflick", "name": "bfi-southbank"},
        {"venue": "old-vic", "status": "stale", "name": "old-vic"},
    ]
    assert soon["generated_at"] == GENERATED


def test_sources_carry_public_credits():
    d = doc({"id": "moth-club:1", "venue": "MOTH Club", "category": "music", "title": "x",
             "start": "2026-11-22T20:00:00+00:00", "booking_url": "https://x"})
    d["sources"] = [
        {"venue": "bfi-southbank", "status": "ok", "attribution": "Screening data from Clusterflick (CC BY 4.0).",
         "source": "Clusterflick open data (https://github.com/clusterflick/data-transformed/releases/x.json)"},
        {"venue": "kings-place", "status": "ok",
         "source": "schema.org Event JSON-LD on https://www.songkick.com/venues/47963-kings-place/calendar"},
        {"venue": "moth-club", "status": "ok", "source": "schema.org Event JSON-LD on https://dice.fm/venue/moth-club-43ox"},
        {"venue": "ica", "status": "ok", "source": "Spektrix ticketing API (https://buy.ica.art/ica/api/v3)"},
    ]
    status = {"venues": [{"venue": "bfi-southbank", "name": "BFI Southbank"}, {"venue": "kings-place", "name": "Kings Place"}]}
    soon, later = web_feed.split(d, status)
    by_slug = {s["venue"]: s for s in soon["sources"]}
    assert by_slug["bfi-southbank"] == {
        "venue": "bfi-southbank", "status": "ok", "attribution": "Screening data from Clusterflick (CC BY 4.0).",
        "name": "BFI Southbank", "via": "Clusterflick", "via_url": "https://clusterflick.com"}
    assert by_slug["kings-place"]["via"] == "Songkick"
    assert by_slug["kings-place"]["via_url"] == "https://www.songkick.com/venues/47963-kings-place/calendar"
    assert by_slug["moth-club"] == {"venue": "moth-club", "status": "ok", "name": "MOTH Club",
                                    "via": "DICE", "via_url": "https://dice.fm/venue/moth-club-43ox"}
    assert "via" not in by_slug["ica"] and by_slug["ica"]["name"] == "ica"
    assert later["sources"] == soon["sources"]


def test_main_writes_compact_files(tmp_path):
    import json
    (tmp_path / "listings.json").write_text(json.dumps(doc(show("today", "2026-11-22T19:00:00+00:00"))))
    web_feed.main(tmp_path)
    text = (tmp_path / "data" / "soon.json").read_text()
    assert ", " not in text and ": " not in text
    assert json.loads(text)["showings"][0]["id"] == "today"
    assert json.loads((tmp_path / "data" / "later.json").read_text())["showings"] == []
