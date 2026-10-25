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
- Old Vic and Almeida: their websites only give run dates; performance times are on Incapsula-protected Tessitura sites.
- National Theatre: CloudFront blocks our requests (403, even robots.txt); its ticketing site is behind Incapsula.
- Young Vic: Cloudflare challenge on youngvic.org; tickets.youngvic.org is a Spektrix front end that isn't challenged (API address not yet found).
