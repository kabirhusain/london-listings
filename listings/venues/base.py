"""The interface every venue module implements."""

from __future__ import annotations

from abc import ABC, abstractmethod

from listings.http import PoliteClient
from listings.model import Showing


class Venue(ABC):
    #: Short stable identifier, used on the command line and in showing ids.
    slug: str
    #: Human-readable venue name, written to each showing's "venue" field.
    name: str
    #: Which source this venue's data comes from and why.
    source_description: str

    @abstractmethod
    def fetch(self, client: PoliteClient) -> list[Showing]:
        """Return upcoming showings. Must only make requests through client."""

    def source_info(self) -> dict:
        """Provenance written to listings.json. Override to add licence credit etc."""
        return {"venue": self.slug, "source": self.source_description}
