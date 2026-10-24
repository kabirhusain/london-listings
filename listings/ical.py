"""Minimal iCalendar (RFC 5545) reader: enough for venue event feeds."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from listings.model import LONDON


def parse_events(text: str) -> list[dict]:
    """Return VEVENTs as dicts: {"SUMMARY": str, "DTSTART": datetime, ...}.

    Property names are upper-cased; parameters are kept under "<NAME>;params".
    """
    # Unfold continuation lines (start with a space or tab).
    lines = re.sub(r"\r?\n[ \t]", "", text).splitlines()
    events, current = [], None
    for line in lines:
        if line == "BEGIN:VEVENT":
            current = {}
        elif line == "END:VEVENT" and current is not None:
            events.append(current)
            current = None
        elif current is not None and ":" in line:
            head, value = line.split(":", 1)
            name, *params = head.split(";")
            name = name.upper()
            if name in ("DTSTART", "DTEND"):
                current[name] = _parse_datetime(value, params)
            else:
                current[name] = _unescape(value)
                if params:
                    current[f"{name};params"] = ";".join(params)
    return events


def _parse_datetime(value: str, params: list[str]) -> datetime:
    tzid = next((p.split("=", 1)[1] for p in params if p.upper().startswith("TZID=")), None)
    if value.endswith("Z"):
        return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    fmt = "%Y%m%dT%H%M%S" if "T" in value else "%Y%m%d"
    dt = datetime.strptime(value, fmt)
    try:
        tz = ZoneInfo(tzid) if tzid else LONDON
    except Exception:
        # e.g. WordPress's "UTC+0", which really means "the site's wall-clock time".
        tz = LONDON
    return dt.replace(tzinfo=tz)


def _unescape(value: str) -> str:
    return value.replace("\\n", "\n").replace("\\N", "\n").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")
