"""Rich Mix (Shoreditch).

Sources (checked 2026-10-24):
- The site is JavaScript-rendered; its calendar is server-rendered one day per
  page (/calendar/YYYY-MM-DD) and /feed.rss has titles and dates only.
- Its Spektrix API (tickets.richmix.org.uk/richmix) only holds a few ticketed
  events, tagged attribute_COGEventProgramme "FILM" / "LIVE".
- Clusterflick publishes Rich Mix's film screenings (CC BY 4.0).
We use Clusterflick for films and Spektrix for music, so neither duplicates the other.
"""

from listings.http import PoliteClient
from listings.model import Showing
from listings.sources.clusterflick import ClusterflickVenue
from listings.sources.spektrix import SpektrixVenue


class _RichMixFilms(ClusterflickVenue):
    slug = "rich-mix"
    name = "Rich Mix"
    clusterflick_id = "richmix.org.uk"


class RichMix(SpektrixVenue):
    slug = "rich-mix"
    name = "Rich Mix"
    api_base = "https://tickets.richmix.org.uk/richmix"

    def __init__(self):
        self._films = _RichMixFilms()

    @property
    def source_description(self) -> str:
        return f"Films: {self._films.source_description}; music: {super().source_description}"

    def category(self, event, instance):
        if event.get("attribute_COGEventProgramme") == "LIVE" and event.get("attribute_COGFirstCategory") == "Music":
            return "music"
        return None

    def details(self, event, instance, category):
        # Rich Mix's music is mostly club nights named after the night, not the
        # acts, so no lineup is guessed.
        return {}

    def fetch(self, client: PoliteClient) -> list[Showing]:
        showings = self._films.fetch(client)
        try:
            showings += super().fetch(client)
        except ValueError:
            pass  # no music on sale right now is normal for Rich Mix
        return sorted(showings, key=lambda s: (s.start, s.title))

    def source_info(self) -> dict:
        return {**self._films.source_info(), "source": self.source_description}


VENUE = RichMix()
