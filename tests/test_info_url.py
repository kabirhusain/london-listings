"""Offline tests for info_url: the central rules and each platform's mapping."""

import json
from datetime import datetime, timedelta

import pytest

from listings.model import LONDON, Showing, clean_info_url, is_checkout_url, london_iso

SOON = datetime.now(LONDON) + timedelta(days=3)


class FakeClient:
    """Serves canned responses by URL substring."""

    def __init__(self, pages):
        self.pages = pages

    def _find(self, url):
        for key, body in self.pages.items():
            if key in url:
                return body
        raise AssertionError(f"unexpected fetch {url}")

    def get(self, url, **kw):
        body = self._find(url)

        class R:
            text = body if isinstance(body, str) else json.dumps(body)
            redirects = []
        R.url = url
        return R

    def get_json(self, url, **kw):
        r = self.get(url)
        return json.loads(r.text), r


# --- central rules ---------------------------------------------------------------

@pytest.mark.parametrize("url", [
    "https://buy.ica.art/ica/website/ChooseSeats.aspx?EventInstanceId=1986801",
    "https://tickets.barbican.org.uk/choose-seats/3791601",
    "https://www.curzon.com/ticketing/seats/BLO1-114307/",
    "https://riocinema.org.uk/Rio.dll/Booking?Booking=TSelectItems.waSelectItemsPrompt.TcsPerformance_1",
    "https://genesis.admit-one.co.uk/seats/?perfCode=13986",
    "https://my.sadlerswells.com/63694/65504",
    "https://my.hampsteadtheatre.com/15424/15489",
    "https://princecharlescinema.com/prince-charles-cinema/booknow/31628024",
    "https://www.eventbrite.com/checkout-external?eid=2003264285404",
    "https://www.electriccinema.co.uk/tickets/80636",
])
def test_checkout_urls_are_recognised(url):
    assert is_checkout_url(url)


@pytest.mark.parametrize("url", [
    "https://www.curzon.com/films/wildwood/HO00007379/?siteId=SOH1",
    "https://riocinema.org.uk/Rio.dll/WhatsOn?f=2910719",
    "https://www.hampsteadtheatre.com/production/dogstar/",
    "https://www.eventbrite.com/e/uppity-the-intellectual-playground-tickets-2003264285404",
])
def test_info_pages_are_not_checkouts(url):
    assert not is_checkout_url(url)


def test_clean_info_url_drops_checkouts_and_duplicates():
    base = {"booking_url": "https://x.org/whats-on/show/"}
    assert clean_info_url(dict(base, info_url="https://x.org/whats-on/show"))["info_url"] is None  # same page
    assert clean_info_url(dict(base, info_url="https://x.org/checkout/1"))["info_url"] is None
    assert clean_info_url(dict(base, info_url="https://x.org/about-show"))["info_url"] == "https://x.org/about-show"


# --- Savoy -----------------------------------------------------------------------------

def test_savoy_uses_the_events_url_field():
    from listings.sources.savoy import SavoyVenue

    events = {"Events": [{
        "ID": 1, "Title": "Film", "RunningTime": 90, "ImageURL": "", "TypeDescription": "Film",
        "URL": "https://riocinema.org.uk/Rio.dll/WhatsOn?f=1",
        "Performances": [{"ID": 7, "StartDate": SOON.strftime("%Y-%m-%d"), "StartTime": "1930",
                          "URL": "Booking?Booking=TSelectItems.waSelectItemsPrompt.TcsPerformance_7"}],
    }]}
    venue = type("V", (SavoyVenue,), {"slug": "rio", "name": "Rio", "whats_on_url": "https://riocinema.org.uk/Rio.dll/WhatsOn"})()
    page = f"<script>var Events = {json.dumps(events)};</script>"
    (s,) = venue.fetch(FakeClient({"WhatsOn": page}))
    assert s.info_url == "https://riocinema.org.uk/Rio.dll/WhatsOn?f=1"
    assert is_checkout_url(s.booking_url)


# --- Clusterflick ---------------------------------------------------------------------------

def _cf_film(url, booking):
    t = int(SOON.timestamp() * 1000)
    return {"showingId": "x-1", "title": "Film", "category": "movie", "overview": {}, "url": url,
            "performances": [{"time": t, "bookingUrl": booking, "screen": "1"}]}


def test_clusterflick_film_url_is_info_url_unless_it_is_the_booking_link():
    from listings.sources.clusterflick import showings_from_clusterflick

    (s,) = showings_from_clusterflick([_cf_film("https://www.curzon.com/films/f/HO1/", "https://www.curzon.com/ticketing/seats/S-1/")],
                                      venue_slug="c", venue_name="C", clusterflick_id="x")
    assert s.info_url == "https://www.curzon.com/films/f/HO1/"
    (s,) = showings_from_clusterflick([_cf_film("https://bfi.example/article", "https://bfi.example/article")],
                                      venue_slug="b", venue_name="B", clusterflick_id="x")
    assert clean_info_url(s.to_dict())["info_url"] is None  # BFI: booking link already is the info page


# --- Spektrix ---------------------------------------------------------------------------------

def test_spektrix_title_matching():
    from listings.sources.spektrix import match_title_to_url
    from listings.text import match_key

    raw = {"The Pianist": "https://p.uk/events/the-pianist/", "Lear": "https://y.uk/events/lear",
           "Lear: The Gala": "https://y.uk/events/lear-gala", "Mojo": "https://p.uk/events/mojo/"}
    links = {match_key(t): u for t, u in raw.items()}  # load_title_links keys by match_key
    assert match_title_to_url("The Pianist", links) == "https://p.uk/events/the-pianist/"
    assert match_title_to_url("Mojo (2026)", links) == "https://p.uk/events/mojo/"
    assert match_title_to_url("The Pianist - Relaxed Performance", links) == "https://p.uk/events/the-pianist/"
    assert match_title_to_url("Something Else Entirely", links) is None
    assert match_title_to_url("Lea", links) is None  # too short for a fuzzy match


def test_spektrix_prefers_weburl_then_page_match():
    from listings.sources.spektrix import SpektrixVenue

    v = type("V", (SpektrixVenue,), {"slug": "v", "name": "V", "api_base": "https://t.uk/v"})()
    v._info_links = {"pianist": "https://p.uk/events/the-pianist/"}  # match_key("The Pianist")
    assert v.info_url({"name": "X", "webUrl": "https://p.uk/events/x/"}) == "https://p.uk/events/x/"
    assert v.info_url({"name": "The Pianist", "webUrl": ""}) == "https://p.uk/events/the-pianist/"


def test_cecil_sharp_info_url_from_cms_id():
    from listings.venues.cecil_sharp_house import VENUE
    assert VENUE.info_url({"attribute_CMSID": "16024"}) == "https://www.efdss.org/whats-on/16024"
    assert VENUE.info_url({"attribute_CMSID": ""}) is None


def test_hackney_empire_reads_titles_and_links_from_cards():
    from bs4 import BeautifulSoup
    from listings.venues.hackney_empire import _event_titles

    html = ('<div class="c-media c-media--event"><h3 class="c-media__title">Henning Wehn: Acid Wehn</h3>'
            '<a href="https://www.hackneyempire.co.uk/events/henning-wehn-acid-wehn">Details</a></div>')
    assert _event_titles(BeautifulSoup(html, "html.parser")) == [
        ("Henning Wehn: Acid Wehn", "https://www.hackneyempire.co.uk/events/henning-wehn-acid-wehn")]


# --- HTML venues ----------------------------------------------------------------------------------

def test_prince_charles_film_page_is_info_url_and_sold_out_duplicates_are_dropped():
    from listings.venues.prince_charles_cinema import parse_whats_on

    day = SOON.strftime("%A ") + str(SOON.day) + "th " + SOON.strftime("%B")
    html = f'''<div class="jacro-event"><a class="liveeventtitle" href="https://princecharlescinema.com/film/1/x">X</a>
      <ul class="performance-list-items"><div class="heading">{day}</div>
        <li><a class="film_book_button" href="https://princecharlescinema.com/prince-charles-cinema/booknow/9"><span class="time">7:30 pm</span></a></li>
        <li><a class="soldfilm_book_button"><span class="time">9:30 pm</span></a></li></ul></div>'''
    shows = sorted(parse_whats_on(html, SOON.date()), key=lambda s: s.start)
    assert [s.info_url for s in shows] == ["https://princecharlescinema.com/film/1/x"] * 2
    assert clean_info_url(shows[0].to_dict())["info_url"] == "https://princecharlescinema.com/film/1/x"
    assert clean_info_url(shows[1].to_dict())["info_url"] is None  # sold out: booking_url is the film page


def test_electric_film_link_is_info_url():
    from listings.venues.electric_cinema import ElectricCinema

    data = {"cinemas": {"603": {"title": "Portobello"}}, "screeningTypes": {},
            "films": {"5": {"title": "Klara", "link": "/film/klara/", "image": False, "rating": "12A"}},
            "screenings": {"1": {"id": 1, "film": "5", "d": SOON.strftime("%Y-%m-%d"), "t": "20:00",
                                 "cinema": "603", "link": "/tickets/1", "bookable": True}}}
    (s,) = ElectricCinema().fetch(FakeClient({"data.json": data}))
    assert s.info_url == "https://www.electriccinema.co.uk/film/klara/"
    assert s.booking_url == "https://www.electriccinema.co.uk/tickets/1"
