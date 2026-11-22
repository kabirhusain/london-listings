"""Offline tests for The Lexington's listing parser (site redesigned Nov 2026)."""

from datetime import date, datetime

from listings.model import LONDON
from listings.venues.the_lexington import VENUE, parse_when

CARDS = """
<div class="events-grid">
<article class="event-card">
  <a class="event-img" href="./event.php?id=3893"><span class="event-label">Gig</span><img src="../uploads/3893.jpg"></a>
  <div class="event-body">
    <p class="event-date">Sun 22nd November · 7:30pm</p>
    <h2 class="event-title"><a href="./event.php?id=3893">Cwfen, Support Act</a></h2>
    <div class="event-actions">
      <a class="pill pill-outline" href="./event.php?id=3893">Read More</a>
      <a class="pill pill-filled" href="https://www.ticketmaster.co.uk/cwfen/event/1">Get Tickets</a>
    </div>
  </div>
</article>
<article class="event-card">
  <a class="event-img" href="./event.php?id=3978"><span class="event-label club">Club</span><img src="../uploads/3978.jpg"></a>
  <div class="event-body">
    <p class="event-date">Fri 27th November · 11pm</p>
    <h2 class="event-title"><a href="./event.php?id=3978">White Heat Club</a></h2>
    <div class="event-actions"><a class="pill pill-filled" href="https://dice.fm/promoters/white-heat">Get Tickets</a></div>
  </div>
</article>
<article class="event-card">
  <a class="event-img" href="./event.php?id=3970"><img src="../uploads/3970.jpg"></a>
  <div class="event-body">
    <p class="event-date">Mon 23rd November · 8pm</p>
    <h2 class="event-title"><a href="./event.php?id=3970">Lexington Pop Quiz</a></h2>
  </div>
</article>
<article class="event-card">
  <div class="event-body">
    <p class="event-date">Sat 21st November · 8pm</p>
    <h2 class="event-title"><a href="./event.php?id=1">Yesterday's gig</a></h2>
  </div>
</article>
</div>
"""


class FakeClient:
    def get(self, url, **_):
        return type("R", (), {"text": CARDS, "url": url})()


def test_parse_when():
    today = date(2026, 11, 22)
    assert parse_when("Sun 22nd November · 7:30pm", today) == datetime(2026, 11, 22, 19, 30, tzinfo=LONDON)
    assert parse_when("Mon 23rd November · 8pm", today) == datetime(2026, 11, 23, 20, 0, tzinfo=LONDON)
    assert parse_when("Sat 2nd January · 12pm", today) == datetime(2027, 1, 2, 12, 0, tzinfo=LONDON)
    # Listed under Friday, but 1am is Saturday morning.
    assert parse_when("Fri 27th November · 1am", today) == datetime(2026, 11, 28, 1, 0, tzinfo=LONDON)
    assert parse_when("Sat October 24, 19:30", today) is None  # the old format


def test_cards(monkeypatch):
    import listings.venues.the_lexington as lex

    class Frozen(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 11, 22, 12, 0, tzinfo=tz)

    monkeypatch.setattr(lex, "datetime", Frozen)
    shows = {s.id: s for s in VENUE.fetch(FakeClient())}
    assert list(shows) == ["the-lexington:3893", "the-lexington:3970", "the-lexington:3978"]
    gig, quiz, club = shows["the-lexington:3893"], shows["the-lexington:3970"], shows["the-lexington:3978"]
    assert gig.lineup == ["Cwfen", "Support Act"]
    assert gig.booking_url == "https://www.ticketmaster.co.uk/cwfen/event/1"
    assert gig.info_url == "https://www.thelexington.co.uk/event.php?id=3893"
    assert gig.image_url == "https://www.thelexington.co.uk/uploads/3893.jpg"
    assert club.tags == ["club-night"] and club.lineup == []
    # No ticket link: book on the event page, and don't repeat it as info_url.
    assert quiz.booking_url == "https://www.thelexington.co.uk/event.php?id=3970" and quiz.info_url is None
    assert quiz.lineup == []
