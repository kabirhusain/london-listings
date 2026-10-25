# Venue survey (2026-10-24)

Each venue's what's-on page was fetched once with our bot user agent (`LondonCinemaListingsBot/0.1`)
after checking robots.txt. "In HTML" means the listings are in the page as served, with no JavaScript needed.

## By ticketing platform

### Spektrix: public JSON API (`<host>/<client>/api/v3/events` + `/instances`). One shared scraper.
| Venue | HTTP | In HTML | Structured source | Status |
|---|---|---|---|---|
| Barbican Cinema | 200 | today only | API `spektrix.barbican.org.uk/barbicancentre` | works (generalise into shared scraper) |
| ICA | 200 | titles and dates, no times | Spektrix web components; API host still to find | to build |
| Rich Mix (film + music) | 200 | no (JS) | API `tickets.richmix.org.uk/richmix` (200); also `/feed.rss` | to build |
| Cecil Sharp House | 200 (redirects to efdss.org/whats-on) | no (JS) | API `sales.efdss.org/efdss` (200); also RSS/Atom feeds | to build |

### Savoy Systems: `var Events = {"Events":[...]}` JSON embedded in the `*.dll` page. One shared scraper.
| Venue | HTTP | In HTML | Structured source | Status |
|---|---|---|---|---|
| Rio Cinema | 200 | yes, as embedded JSON | `riocinema.org.uk/Rio.dll/WhatsOn` | to build |
| The Lexi | 200 | yes, as embedded JSON | `thelexicinema.co.uk/TheLexiCinema.dll/WhatsOn` | to build |
| Phoenix Cinema | 200 | yes, as embedded JSON | `phoenixcinema.co.uk/PhoenixCinemaLondon.dll/...` | to build |
| The Garden Cinema | 200 | yes (HTML, 366 times) | Savoy booking site `bookings.thegardencinema.co.uk/TheGardenCinema.dll/`; check it for embedded JSON | to build |

### DICE: widget / partners API (`partners-endpoint.dice.fm/api/v2/events`) with the venue's own public key and venue filter. One shared scraper.
| Venue | HTTP | In HTML | Structured source | Status |
|---|---|---|---|---|
| MOTH Club | 200 | no (JS) | DICE partners API; key and venue in page | to build |
| Folklore | 200 | no (DICE widget iframe) | DICE widget config in page (`venues: ["Folklore Hoxton"]`) | to build |
| Cafe Oto | 200 | yes | HTML list; DICE links | to build (HTML) |
| Union Chapel | 200 | yes (dates; times on event pages) | HTML; DICE + Gigantic | to build (HTML) |
| St Pancras Old Church | n/a | n/a | no website of its own; listed on DICE / Songkick | manual |

### The Events Calendar (WordPress plugin): REST `/wp-json/tribe/events/v1/events`, iCal, JSON-LD. One shared scraper.
| Venue | HTTP | In HTML | Structured source | Status |
|---|---|---|---|---|
| The Cinema Museum | 200 (`/schedule/`) | yes, plus 12 Event JSON-LD | REST + iCal `?ical=1`; tickets via Ticketlab | to build |
| Vortex Jazz Club | 200 | yes | REST + iCal `/events/?ical=1`; tickets via Universe | to build |

### Blocked: Cloudflare challenge (no bypass). Use Clusterflick open data where it exists.
| Venue | HTTP | Notes | Status |
|---|---|---|---|
| BFI Southbank (AudienceView) | 403 challenge | | works via Clusterflick |
| Curzon Soho (Vista) | 403 challenge, even robots.txt | | Clusterflick `curzon.com-soho` |
| Curzon Bloomsbury (Vista) | 403 challenge, even robots.txt | | Clusterflick `curzon.com-bloomsbury` |
| Close-Up Film Centre | 403 challenge, even robots.txt | | Clusterflick `closeupfilmcentre.com` |
| Kings Place | 403 custom JS challenge, even robots.txt | not on Clusterflick | manual |
| Ronnie Scott's | 403 Cloudflare challenge | not on Clusterflick | manual |
| Bush Hall | 429 from Cloudflare on first request (`retry-after: 60`) | retry once in phase 3 | probably manual |

### Disallowed by robots.txt
| Venue | HTTP | Notes | Status |
|---|---|---|---|
| Regent Street Cinema (INDY) | 200 (JS shell) | only data source `/graphql` is disallowed | works via Clusterflick |

### Single-venue / own systems
| Venue | Platform | HTTP | In HTML | Structured source | Plan |
|---|---|---|---|---|---|
| Prince Charles Cinema | Jack Roe | 200 | yes | none, one server-rendered page | works |
| Electric Cinema (Notting Hill) | Vista via Soho House site | 200 | no (JS) | JSON endpoint `/data/data.json` (200, 39 KB) | to build |
| Ciné Lumière | Savoy booking + AEC app | 200 | partial | JSON API `iflondres.aec.app/api/` with public key in page | to build |
| Genesis Cinema | Admit One | 200 | yes (315 times) | none | HTML |
| The Castle Cinema | own | 200 | tiles only; `/calendar/` has times | MovieTheater JSON-LD only | HTML (`/calendar/`) |
| The Nickel | own (Next.js) | 200 | yes (193 times) | none | HTML |
| Bertha DocHouse | WordPress; tickets via Curzon | 200 | dates, no times | none; per-film pages | HTML (not on Clusterflick) |
| Green Note | WeGotTickets | 200 | yes (`/upcoming_events`) | none | HTML |
| The Slaughtered Lamb | See Tickets (Urban Pubs & Bars site) | 200 (redirects) | yes | none | HTML |
| The Troubadour | Wix; DICE/Ticketweb/Universe | 200 (`troubadourlondon.com`; old troubadour.co.uk lapsed) | partly | Wix | HTML, probably fragile |
| The Lexington | mixed (DICE, See Tickets, WeGotTickets...) | 200 (`/events.php`) | yes | none | HTML |
| 606 Club | own | 200 (`/events/`) | partly | none | HTML; may need per-month pages |
| PizzaExpress Live Soho | own | 200 | no, but `__NEXT_DATA__` | JSON API `api.pizzaexpresslive.com` | API |

## Reference projects

- **Joeboy/cinescrapers**: no licence file, so all rights reserved. Read for approach only, don't copy code.
  Last push Aug 2025. Covers BFI, Garden, ICA, Rio, Genesis, Close-Up, Bertha, Ciné Lumière, Rich Mix,
  Castle, Phoenix, Lexi, Electric, Regent Street, PCC, Barbican. All use Playwright with CSS selectors.
  Rio/Lexi read the Savoy `Events` JS object.
- **clusterflick/scripts**: MIT licence, so code can be reused with the copyright notice. Active (pushed today).
  It has shared modules for `savoysystems.co.uk`, `spektrix.js`, `tribe-events`, `admit-one.co.uk`,
  `electriccinema.co.uk` (`/data/data.json`), `thecastlecinema.com` (`/calendar/`), `curzon.com`, and
  venue scrapers for most cinemas above plus Cafe Oto, MOTH, Folklore and Union Chapel (film events only).
  Some of its modules use stealth browsers (camoufox) for bot challenges; we won't port those parts.
- **Clusterflick data** (CC BY 4.0) is the fallback for blocked cinemas. It only has film events, so
  it can't stand in for music venues.

## Phase 3 outcome (2026-10-24)

Final source per venue, with the showings returned on the first full run (3,940 total, 0 errors).

| Venue | Module | Source | Showings |
|---|---|---|---|
| BFI Southbank | bfi_southbank | Clusterflick (site blocked) | 359 |
| The Garden Cinema | garden_cinema | homepage HTML | 159 |
| Regent Street Cinema | regent_street_cinema | Clusterflick (/graphql disallowed) | 35 |
| Prince Charles Cinema | prince_charles_cinema | /whats-on/ HTML | 681 |
| Barbican Cinema | barbican_cinema | Spektrix API + day pages | 144 |
| ICA | ica | Spektrix API (buy.ica.art) | 217 (180 film, 37 music) |
| Curzon Soho | curzon_soho | Clusterflick (site blocked) | 131 |
| Curzon Bloomsbury | curzon_bloomsbury | Clusterflick, minus DocHouse screen | 220 |
| Rio Cinema | rio_cinema | Savoy embedded JSON | 94 |
| Genesis Cinema | genesis_cinema | homepage HTML | 141 |
| Close-Up Film Centre | close_up_film_centre | Clusterflick (site blocked) | 64 |
| Bertha DocHouse | bertha_dochouse | Clusterflick Curzon Bloomsbury, DocHouse screen | 72 |
| Ciné Lumière | cine_lumiere | Clusterflick (site API needs embedded key) | 267 |
| Rich Mix | rich_mix | Clusterflick films + Spektrix music | 10 |
| The Castle Cinema | castle_cinema | /calendar/ data attributes | 77 |
| Phoenix Cinema | phoenix_cinema | Savoy embedded JSON | 70 |
| The Lexi | the_lexi | Savoy embedded JSON | 154 |
| Electric Cinema (Notting Hill) | electric_cinema | /data/data.json | 27 |
| The Nickel | the_nickel | homepage HTML | 73 |
| The Cinema Museum | cinema_museum | The Events Calendar REST API | 47 |
| Green Note | green_note | RSS feed (/upcoming_events) | 162 |
| Cecil Sharp House | cecil_sharp_house | Spektrix API (sales.efdss.org) | 26 |
| Kings Place | kings_place | Songkick calendar JSON-LD (site blocked) | 49 |
| Union Chapel | union_chapel | listing HTML + event pages | 98 |
| The Troubadour | the_troubadour | Wix Events JSON in page | 16 |
| The Slaughtered Lamb | slaughtered_lamb | Songkick calendar JSON-LD | 1 |
| Ronnie Scott's | ronnie_scotts | Songkick calendar JSON-LD (site blocked) | 59 |
| Vortex Jazz Club | vortex_jazz_club | iCal feed | 66 |
| PizzaExpress Live Soho | pizzaexpress_live_soho | public JSON API | 153 |
| 606 Club | club_606 | weekly HTML pages | 41 |
| Cafe Oto | cafe_oto | paginated HTML | 43 |
| MOTH Club | moth_club | DICE venue page JSON-LD | 29 |
| Folklore | folklore | Songkick calendar JSON-LD | 5 |
| The Lexington | the_lexington | /events.php HTML | 90 |
| Bush Hall | bush_hall | Songkick calendar JSON-LD (site returns 429) | 37 |
| St Pancras Old Church | st_pancras_old_church | DICE venue page JSON-LD | 25 |

Not used, on purpose: DICE partner API and Ciné Lumière's AEC API. Both need API keys embedded in
the venues' pages, and reusing those keys was blocked by the permission system.


## Theatres and more (added 2026-10-25)

| Venue | Module | Source |
|---|---|---|
| Royal Court, Donmar Warehouse, Bush, Kiln (theatre + cinema), Arcola, Soho Theatre, Battersea Arts Centre, Orange Tree, Park, Gate, Unicorn, Lyric Hammersmith, Stratford East, Southwark Playhouse, The Yard | one file each | Spektrix API, per-venue attribute rules for category |
| Hackney Empire | hackney_empire | Spektrix API; categories from the venue's own /whats-on/category/ pages |
| Barbican Centre (theatre, dance, concerts) | barbican_centre | same Spektrix API as barbican_cinema (cached) |
| Hampstead Theatre | hampstead_theatre | production pages on hampsteadtheatre.com (ticketing site is Incapsula-protected) |
| Sadler's Wells (Angel + Lilian Baylis Studio) | sadlers_wells | show pages on sadlerswells.com (ticketing site is Incapsula-protected) |

Not added:
- Old Vic and Almeida: added as run entries (kind="run": first/last dates, no times) from their own sites; performance times are only on Incapsula-protected Tessitura sites.
- National Theatre: CloudFront blocks our requests (403, even robots.txt); its ticketing site is behind Incapsula; no allowed structured source for run dates. Use a manual run file.
- Young Vic: Cloudflare challenge on youngvic.org; tickets.youngvic.org is a Spektrix front end that isn't challenged (API address not yet found).

## info_url survey (Prompt 4 phase 2, 2026-10-25)

"Per production" = all performances of a film/show share the URL. "null" = booking_url
already is the public event page, so info_url stays null.

| Platform / venue | Where info_url comes from | Example | Granularity |
|---|---|---|---|
| Savoy (Rio, Lexi, Phoenix) | `URL` field already in the embedded Events JSON | riocinema.org.uk/Rio.dll/WhatsOn?f=2910719 | per production |
| Clusterflick: Curzon Soho/Bloomsbury, Bertha DocHouse | film `url` in Clusterflick data | curzon.com/films/big-girls-dont-cry/HO00007471/?siteId=BLO1 | per production |
| Clusterflick: Ciné Lumière | film `url` | institut-francais.org.uk/cinema/a-good-little-soldier/ | per production |
| Clusterflick: Close-Up | film `url` | closeupfilmcentre.com/film_programmes/2026/.../all-white-in-barking | per production |
| Clusterflick: Regent Street | film `url` | regentstreetcinema.com/movie/42nd-street | per production |
| Clusterflick: Rich Mix films | film `url` (Eventbrite event page; booking is checkout) | eventbrite.com/e/...-2003769106337 | per production |
| Clusterflick: BFI Southbank | `url` == booking (article page, not a checkout) | whatson.bfi.org.uk/...article_id=... | null |
| Prince Charles | film link on the scraped page | princecharlescinema.com/film/31617175/... | per production |
| Garden | film link on the scraped homepage | thegardencinema.co.uk/film/all-about-the-money-qa/ | per production |
| Genesis | `event/<id>` link on the scraped homepage | genesiscinema.co.uk/event/112569 | per production |
| Castle | `/programme/<id>/<slug>/` tile link on the scraped calendar | thecastlecinema.com/programme/113504/wildwood/ | per production |
| Electric | film `link` in data.json (booking is `/tickets/<id>`) | electriccinema.co.uk/film/you-can-see-everything/ | per production |
| Barbican Cinema | event link from the day listings already fetched (matched by instance id) | barbican.org.uk/whats-on/2026/event/... | per production |
| The Nickel | booking_url is `/screening/<id>`, the info page | thenickel.co.uk/screening/780 | null |
| Hampstead | production page already fetched | hampsteadtheatre.com/production/dogstar/ | per production |
| Sadler's Wells | show page already fetched | sadlerswells.com/whats-on/culture-club-2026/ | per production |
| Hackney Empire | event links on the category pages already fetched (matched by title) | hackneyempire.co.uk/events/henning-wehn-acid-wehn | per production |
| Union Chapel | event link on the listing already fetched | unionchapel.org.uk/whats-on/ezra-furman-solo | per event |
| Lexington | `event.php?id=` link on the listing | thelexington.co.uk/event.php?id=3889 | per event |
| Troubadour | Wix event `slug` | troubadourlondon.com/event-details/<slug> | per event |
| Cecil Sharp House | EFDSS RSS feed (1 request) matched on Spektrix `attribute_CMSID` | efdss.org/whats-on/15993-... | per production |
| Spektrix: Park, Yard | `webUrl` in the API (Park 9/36, Yard 6/8) | parktheatre.co.uk/events/the-weddings/ | per production |
| Spektrix: other theatres, ICA, Barbican Centre, Rich Mix music | no URL in the API; would need the venue's what's-on page (1 request per venue) matched by title: Bush 100%, Unicorn 90%, Orange Tree 87%, Stratford East 83%, Southwark 77%, Park 75%, Lyric 50%, Royal Court 40%, BAC 38%, Kiln 28%, Soho 26%, ICA 16%, Barbican 1%, Donmar/Arcola/Yard 0% | bushtheatre.co.uk/event/insane-asylum-seekers-2026/ | per production |
| PizzaExpress, 606, Cafe Oto, Green Note, Vortex, Cinema Museum, Almeida, Old Vic | booking_url is already the event page | | null |
| DICE (MOTH, St Pancras Old Church) | booking_url is the DICE event page (info + buy, not a checkout) | dice.fm/event/... | null |
| Songkick (Kings Place, Ronnie Scott's, Bush Hall, Folklore, Slaughtered Lamb) | booking_url is the Songkick concert page | songkick.com/concerts/... | null |
