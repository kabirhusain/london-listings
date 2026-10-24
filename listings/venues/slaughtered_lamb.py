"""The Slaughtered Lamb (Clerkenwell).

Source (checked 2026-10-24): the pub's site (now on Urban Pubs & Bars, Webflow)
only has a generic "Live Music" card, no gig list; gigs are sold on See
Tickets / WeGotTickets. Songkick's venue calendar (/calendar) has MusicEvent JSON-LD with
performers. It's crowd-sourced and sparse, so this venue is a good
candidate for the manual/ folder.
"""

from listings.sources.jsonld import JsonLdEventsVenue


class SlaughteredLamb(JsonLdEventsVenue):
    slug = "slaughtered-lamb"
    name = "The Slaughtered Lamb"
    page_url = "https://www.songkick.com/venues/6950-slaughtered-lamb/calendar"
    max_pages = 3
    title_suffix = "@ Slaughtered Lamb"


VENUE = SlaughteredLamb()
