"""Runs each venue's collector for real and checks the output against the schema.

    python -m pytest -m network          # just these
    python -m pytest -m "not network"    # skip them (offline)
"""

from datetime import datetime, timedelta

import pytest

from listings.__main__ import collect
from listings.http import PoliteClient
from listings.model import LONDON, validate_listings
from listings.venues import all_venues

# Expected per-venue minimums. A sudden drop below these means a source broke.
# Roughly a third of what each venue returned on 2026-10-24.
MIN_SHOWINGS = {
    "barbican-cinema": 40, "bfi-southbank": 100, "bertha-dochouse": 20, "cine-lumiere": 80,
    "close-up-film-centre": 20, "curzon-bloomsbury": 70, "curzon-soho": 40, "electric-cinema": 8,
    "garden-cinema": 50, "genesis-cinema": 40, "ica": 60, "phoenix-cinema": 20, "prince-charles-cinema": 200,
    "regent-street-cinema": 10, "rio-cinema": 30, "the-lexi": 50, "the-nickel": 20, "castle-cinema": 25,
    "cinema-museum": 15, "rich-mix": 3,
    "cecil-sharp-house": 8, "green-note": 50, "union-chapel": 30, "the-troubadour": 5, "kings-place": 15,
    "ronnie-scotts": 20, "vortex-jazz-club": 20, "pizzaexpress-live-soho": 50, "606-club": 12, "cafe-oto": 15,
    "moth-club": 10, "the-lexington": 30, "bush-hall": 12, "st-pancras-old-church": 8,
    "folklore": 1, "slaughtered-lamb": 0,
}
# Venues whose source gives film runtimes; a drop means a field moved.
RUNTIME_EXPECTED = {
    "bfi-southbank", "barbican-cinema", "prince-charles-cinema", "regent-street-cinema", "ica", "rio-cinema",
    "the-lexi", "phoenix-cinema", "genesis-cinema", "the-nickel", "curzon-soho", "curzon-bloomsbury",
    "close-up-film-centre", "bertha-dochouse", "cine-lumiere",
}


@pytest.mark.network
@pytest.mark.parametrize("slug", sorted(all_venues()))
def test_venue_live_output_matches_schema(slug):
    # No cache: the point is to check the live source still works.
    doc, errors = collect([slug], PoliteClient(cache_dir=None))
    assert errors == []
    validate_listings(doc)

    showings = doc["showings"]
    venue_name = all_venues()[slug].name
    assert {s["venue"] for s in showings} == {venue_name}
    assert len(showings) >= MIN_SHOWINGS.get(slug, 1)
    if not showings:
        return
    assert all(s["id"].startswith(f"{slug}:") for s in showings)
    assert {s["category"] for s in showings} <= {"film", "music"}

    now = datetime.now(LONDON)
    starts = [datetime.fromisoformat(s["start"]) for s in showings]
    assert min(starts) >= now - timedelta(minutes=1)
    assert max(starts) <= now + timedelta(days=730)

    # Most films should have a runtime; a sudden drop means a field moved.
    films = [s for s in showings if s["category"] == "film"]
    if films and slug in RUNTIME_EXPECTED:
        assert sum(1 for s in films if s["runtime_minutes"]) / len(films) > 0.6
