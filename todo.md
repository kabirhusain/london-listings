## Prompt 3

Good. Now expand the collector to cover all my venues, cinemas and music. Work through this in phases and report back after each phase before continuing.

PHASE 1: Extend the schema
Add these fields to every showing in listings.json: "category" ("film" or "music"), "lineup" (list of artists, headliner first; empty for films), "doors" (time or null), "price" (text such as "From £16", or null), and "genre" (text or null). Make sure "runtime_minutes" and "image_url" allow null. Set category to "film" for all existing cinema scrapers, and update the tests to validate the new schema.

PHASE 2: Survey before writing code
For every venue below, including the ones that already work, visit its what's-on page and find out:
- Whether listings are available as structured data (JSON-LD, iCal/RSS feeds, or a JSON endpoint the page calls), are JavaScript-rendered, or sit behind bot protection. For each, report the HTTP status code and whether the listings appear in the initial HTML.
- Which ticketing platform it uses (e.g. Spektrix, WeGotTickets, See Tickets, DICE, its own system).
Give me a table of the results, grouped by ticketing platform. Where several venues share a platform, plan one shared scraper for that platform instead of one per venue. Also check the open-source cinescrapers project on GitHub (Joeboy/cinescrapers) for working approaches to any of these venues, and tell me what's reusable and under what license.

PHASE 3: Build the scrapers, in priority order
Skip any venue whose scraper already works. Test each new one before moving on. Use the most structured source available. For JavaScript-rendered pages, first look for the JSON endpoint the page calls and use that directly; only fall back to Playwright if there isn't one. Respect robots.txt, identify with a clear user agent, and add delays between requests. Don't bypass bot protection: if a venue blocks you, record it as blocked and move on.

Cinemas, core: BFI Southbank, The Garden Cinema, Regent Street Cinema, Prince Charles Cinema, Barbican Cinema, ICA, Curzon Soho, Curzon Bloomsbury
Cinemas, next: Rio Cinema, Genesis Cinema, Close-Up Film Centre, Bertha DocHouse, Ciné Lumière, Rich Mix, The Castle Cinema, Phoenix Cinema (East Finchley), The Lexi, Electric Cinema (Notting Hill)
Cinemas, try last: The Nickel, The Cinema Museum
Music, core: Green Note, Cecil Sharp House, Kings Place, Union Chapel, The Troubadour, The Slaughtered Lamb
Music, jazz: Ronnie Scott's, Vortex Jazz Club, PizzaExpress Live Soho, 606 Club, Cafe Oto
Music, small gig venues: MOTH Club, Folklore, The Lexington, Bush Hall, St Pancras Old Church

PHASE 4: Manual fallback for difficult venues
Create a manual/ folder where I can drop a JSON file per venue in the same schema, for venues I enter by hand each month. The merge step should include these and ignore any entries whose dates have passed.

PHASE 5: Merge, resilience, and scheduling
Keep the existing merge, failure handling, and GitHub Actions workflow, and extend them:
- Normalise film titles for matching (e.g. "&" vs "and", anniversary or format suffixes) so the same film at different venues groups together.
- Write a status.json listing each venue, when it last succeeded, and how many listings it returned, and publish it to GitHub Pages alongside listings.json.
- If some venues block GitHub's servers but work from my own computer, tell me which ones, and set up an alternative way to run the collector locally on a schedule and push the results.
- Update the README to cover the manual/ folder and status.json.

At the end, give me a summary: which venues work, which use the manual fallback, which failed and why, what I should do about each failure, and the public URL of listings.json.

## Prompt 2

Add scrapers for Regent Street Cinema, Prince Charles Cinema, and Barbican Cinema using the same venue interface and the same "most structured source first" approach. Then:
- Merge all venues into one listings.json, deduplicated and sorted by start time.
- If one venue's scraper fails, log the error and still publish the others (keep that venue's last good data if available).
- Add a GitHub Actions workflow that runs daily at 6am London time and publishes listings.json to GitHub Pages.
- Write a short README explaining how to add a new venue.

## Prompt 1

I'm building an app that aggregates cinema listings from London venues. Start with the backend data collector only, no app yet.

Set up a Python project that:
- Fetches upcoming listings for BFI Southbank (start with just this venue).
- Before scraping HTML, checks for cleaner sources: schema.org Event JSON-LD in the page, an iCal/RSS feed, or a ticketing platform API the site loads data from. Use the most structured source you can find, and tell me which you chose and why.
- Checks robots.txt and respects it. Fetch politely: identify with a clear user agent, add delays between requests, and don't hit the site more than needed.
- Outputs a single listings.json in this schema:
  { "generated_at", "showings": [ { "id", "venue", "title", "start" (ISO 8601, Europe/London), "runtime_minutes", "booking_url", "image_url", "tags" } ] }
- Structures each venue as its own module behind a common interface, so adding venues later means adding one file.
- Has a simple test that runs the BFI scraper and validates the output against the schema.

Run it, show me a sample of the output, and flag anything that looks fragile.