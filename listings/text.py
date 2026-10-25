"""Text helpers shared by venue scrapers."""

from __future__ import annotations

import html
import re

_MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*"
_SEASON = r"(?:spring|summer|autumn|winter)"
# Box-office housekeeping suffixes, e.g. "Elanor Moss 2026", "Morris Dancing Autumn 2026",
# "Queer Ceilidh Dance Party Nov 2026".
_YEAR_SUFFIX = re.compile(rf"\s+(?:(?:{_MONTH}|{_SEASON})\s+)?20\d\d$", re.I)


def tidy_title(title: str) -> str:
    """Unescape HTML entities, collapse whitespace, drop box-office year suffixes
    ("Elanor Moss 2026") - but only for years near now, so "Disco 2000" survives."""
    from datetime import date

    t = re.sub(r"\s+", " ", html.unescape(title)).strip()
    m = _YEAR_SUFFIX.search(t)
    if m and abs(int(m.group(0)[-4:]) - date.today().year) <= 1:
        t = t[: m.start()].strip() or t
    return t


# Separators between acts in a gig title: "A + B", "A / B", "A, B & C", "A with B".
_ACT_SPLIT = re.compile(r"\s+\+\s+|\s+/\s+|\s*,\s+|\s+&\s+(?=[A-Z])|\s+(?:with|w/|ft\.?|feat\.?|featuring|support from|special guests?:?)\s+", re.I)
_SERIES = r"night|presents|club|session|series|festival|showcase|residency|launch"
# Things after a colon or dash that describe the show rather than name an act.
_SUBTITLE = re.compile(r"\s*(?::|\s[-–—]\s|\(|\s+live (?:at|in|from)\b).*$", re.I)


def guess_lineup(title: str) -> list[str]:
    """Best-effort lineup from a gig title when the source has no structured
    lineup. "Hugh Cornwell: Never Say Goodbye" -> ["Hugh Cornwell"];
    "Moor Mother + Guest" -> ["Moor Mother", "Guest"]. Headliner first."""
    t = tidy_title(title)
    # "Trad Night: Macdara Yeates" - the series name comes first, the act second.
    series = re.match(rf"^[^:]*\b(?:{_SERIES})\b[^:]*:\s*(.+)$", t, re.I)
    if series:
        t = series.group(1)
    # "A Homemade Evening with Nara Smith", "An Evening With X" -> X
    t = re.sub(r"^.*?\b(?:evening|afternoon|night|morning)\s+with\s+", "", t, flags=re.I)
    head = _SUBTITLE.sub("", t).strip() or t
    acts = [a.strip(" -–—|") for a in _ACT_SPLIT.split(head)]
    acts = [re.sub(r"^(?:very\s+)?special\s+guests?:?\s+", "", a, flags=re.I) for a in acts]
    acts = [a for a in acts if not re.fullmatch(r"(?:his|her|their|the)?\s*(?:band|orchestra|friends)", a, re.I)]
    return list(dict.fromkeys(a for a in acts if a and len(a) > 1))


_DAY_MONTH = re.compile(
    r"^(?:(?P<weekday>[A-Za-z]+),?\s+)?(?P<day>\d{1,2})(?:st|nd|rd|th)?\s+(?P<month>[A-Za-z]+)\.?(?:\s+(?P<year>\d{4}))?$"
)


def date_without_year(text: str, today):
    """'Saturday 24th October' / 'Sat 24 Oct' -> a date. When there's no year,
    take the first of this year / next year (or last year, around New Year) where
    the date isn't in the past and, if a weekday is given, falls on it."""
    from datetime import datetime, timedelta

    m = _DAY_MONTH.match(text.strip())
    if not m:
        return None
    years = [int(m.group("year"))] if m.group("year") else [today.year, today.year + 1, today.year - 1]
    for year in years:
        for fmt in ("%d %B %Y", "%d %b %Y"):
            try:
                d = datetime.strptime(f"{m.group('day')} {m.group('month')[:3] if fmt.endswith('%b %Y') else m.group('month')} {year}", fmt).date()
                break
            except ValueError:
                d = None
        if d is None:
            continue
        weekday = m.group("weekday")
        if weekday and not d.strftime("%A").lower().startswith(weekday.lower()[:3]):
            continue
        if m.group("year") or d >= today - timedelta(days=1):
            return d
    return None


_CLOCK = r"(\d{1,2}(?:[:.]\d{2})?\s*(?:am|pm)|\d{1,2}[:.]\d{2})"
_DOORS = re.compile(rf"\bdoors?(?:\s+open)?(?:\s+at)?\s*[:\-–]?\s*{_CLOCK}", re.I)
_START = re.compile(
    rf"\b(?:starts?|start time|show(?:time)?|music|performance|concert|stage|gig|event|onstage|on stage|headliner)"
    rf"(?:\s+(?:starts?|from|at|time))?\s*[:\-–]?\s*{_CLOCK}",
    re.I,
)


def parse_clock(s: str):
    """'7.30pm' / '7pm' / '19:30' -> datetime.time (None if unparseable)."""
    from datetime import time as dtime

    m = re.match(r"^(\d{1,2})(?:[:.](\d{2}))?\s*(am|pm)?$", s.strip(), re.I)
    if not m:
        return None
    hour, minute, ampm = int(m.group(1)), int(m.group(2) or 0), (m.group(3) or "").lower()
    if ampm == "pm" and hour < 12:
        hour += 12
    elif ampm == "am" and hour == 12:
        hour = 0
    elif not ampm and m.group(2) and 1 <= hour <= 10:
        hour += 12  # a bare "7.30" in a gig listing means the evening
    if hour > 23 or minute > 59:
        return None
    return dtime(hour, minute)


def find_doors_and_start(text: str):
    """Doors and start times mentioned in free text, as datetime.time (either may be None)."""
    d = _DOORS.search(text)
    s = _START.search(text)
    return (parse_clock(d.group(1)) if d else None, parse_clock(s.group(1)) if s else None)


# --- matching the same film/show across venues -------------------------------

# A "Series: Title" prefix is dropped only if the series part looks like a
# programme strand, not part of the title ("Dune: Part Two" keeps its colon).
_SERIES_PREFIX = re.compile(
    r"^(?P<series>[^:]{1,60}?)\s*:\s+(?=\S)",
)
_SERIES_WORDS = re.compile(
    r"screening|preview|club|festival|\bfest\b|\bff[a-z]?\b|season|presents|\bcinema\b|week(?:ender)?|"
    r"spotlight|off-circuit|doc ?day|classroom|on screen|members|relaxed|parent|baby|senior|family|"
    r"classics|nt live|met opera|\brbo\b|royal ballet|lpff|ukjff|liaf|lkff|in-edit|nfts|film50|"
    r"doc'?n'?roll|dochouse|kids|toddler|matin[ée]e|special|event|strand|focus|retrospective|"
    r"[a-z].*\b20[1-3]\d\b",  # "LPFF 2026", but not "2001: A Space Odyssey"
    re.I,
)
# Extras and versions appended to a title: "+ Q&A", "- 25th Anniversary", "(4K Restoration)", "(1978)".
_EXTRA_SUFFIX = re.compile(r"\s+\+\s+.*$")
_ANNIVERSARY = re.compile(r"\s*[-–:(\[]?\s*\d{1,3}(?:st|nd|rd|th)\s+anniversary(?:\s+[a-z ]+)?[)\]]?\s*$", re.I)
_FORMAT_WORDS = (
    r"2d|3d|4k|imax|35 ?mm|16 ?mm|70 ?mm|restor(?:ed|ation)|remaster(?:ed)?|re-?release|dubbed|subtitled|"
    r"uk version|(?:uk|world|london|european) premiere|digital|dcp|sing[- ]?a?[- ]?long|hoh|ad|bsl|relaxed"
)
# A format word must be a whole word set off by a space, dash or bracket ("Shaun of the Dead" keeps its "ad").
_FORMAT_SUFFIX = re.compile(
    rf"(?:\s+(?:on|in)\s+|\s*[-–]\s*|\s*[(\[]\s*|\s+)(?:{_FORMAT_WORDS})\b(?:\s+(?:{_FORMAT_WORDS})\b)*\s*[)\]]?\s*$",
    re.I,
)
_BRACKETED = re.compile(r"\s*\[[^\]]*\]|\s*\((?:19|20)\d\d\)|\s*\((?:u|pg|12a?|15|18)\*?\)", re.I)


def match_key(title: str) -> str:
    """A normalised key so the same film (or show) lines up across venues.

    "Your Name [Kimi no Na wa.]", "YOUR NAME (4K Restoration)" and
    "Preview: Your Name + Q&A" all give "your name". Director's / extended
    cuts are kept distinct on purpose.
    """
    import unicodedata

    t = tidy_title(title)
    for _ in range(2):  # "LPFF 2026: Preview: X"
        m = _SERIES_PREFIX.match(t)
        if m and _SERIES_WORDS.search(m.group("series")):
            t = t[m.end():]
    t = _EXTRA_SUFFIX.sub("", t)
    for _ in range(3):  # suffixes can stack: "X (1978) - 40th Anniversary (4K)"
        before = t
        t = _BRACKETED.sub("", t)
        t = _ANNIVERSARY.sub("", t)
        t = _FORMAT_SUFFIX.sub("", t)
        if t == before:
            break
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    t = t.lower().replace("&", " and ")
    t = re.sub(r"['’`]", "", t)
    t = re.sub(r"[^a-z0-9]+", " ", t).strip()
    t = re.sub(r"^(?:the|a|an)\s+", "", t)
    return t or tidy_title(title).lower()


_D = r"(?:(?:mon|tue|wed|thu|fri|sat|sun)[a-z]*\.?,?\s+)?"  # optional weekday
_RANGE = re.compile(
    rf"{_D}(?P<d1>\d{{1,2}})(?:st|nd|rd|th)?(?:\s+(?P<m1>[a-z]{{3,9}})\.?)?(?:\s+(?P<y1>\d{{4}}))?"
    rf"\s*(?:[–—-]|to|until)\s*"
    rf"{_D}(?P<d2>\d{{1,2}})(?:st|nd|rd|th)?\s+(?P<m2>[a-z]{{3,9}})\.?\s+(?P<y2>\d{{4}})",
    re.I,
)
_SINGLE = re.compile(rf"{_D}(?P<d>\d{{1,2}})(?:st|nd|rd|th)?\s+(?P<m>[a-z]{{3,9}})\.?\s+(?P<y>\d{{4}})", re.I)


def _month(name: str) -> int | None:
    from datetime import datetime

    for fmt, value in (("%B", name), ("%b", name[:3])):
        try:
            return datetime.strptime(value, fmt).month
        except ValueError:
            continue
    return None


def parse_date_range(text: str):
    """Day-precise date range from text, e.g. "Tue 10 Nov – Wed 23 Dec 2026",
    "10 Nov 2026–09 Jan 2027", "01–31 Oct 2026", "19 Dec 2026".
    Returns (first, last) dates, or None (including for vague text like "Jun - Jul 2027")."""
    from datetime import date

    m = _RANGE.search(text)
    if m:
        d1, d2 = int(m.group("d1")), int(m.group("d2"))
        m2, y2 = _month(m.group("m2")), int(m.group("y2"))
        m1 = _month(m.group("m1")) if m.group("m1") else m2
        if not (m1 and m2):
            return None
        # "Sat 21 Nov - Sat 17 Apr 2026": the first date is in the previous year.
        y1 = int(m.group("y1")) if m.group("y1") else (y2 if (m1, d1) <= (m2, d2) else y2 - 1)
        try:
            return date(y1, m1, d1), date(y2, m2, d2)
        except ValueError:
            return None
    m = _SINGLE.search(text)
    if m and _month(m.group("m")):
        try:
            d = date(int(m.group("y")), _month(m.group("m")), int(m.group("d")))
            return d, d
        except ValueError:
            return None
    return None


# --- blurbs ---------------------------------------------------------------------

BLURB_MAX = 280
_BOILERPLATE = re.compile(
    r"£|\btickets?\b|\bbook(?:ing)?\b|please note|doors?\b|\bbar\b|running time|certificate|"
    r"\bdir(?:ected by|\.)\s|\bstarring\b|\bcast\b|https?://|www\.|\bfaqs?\b|house rules|age restriction|"
    r"\bmembers?\b|concessions?|wheelchair|captioned|audio[- ]described|subtitled screening|"
    r"^\s*(?:about|line-?up)\s*:?\s*$",
    re.I,
)
_SCREENING_NOTE = re.compile(
    r"\bq ?& ?a\b|followed by|introduced by|introduction (?:by|from)|this screening|the screening on|"
    r"screening on (?:mon|tues|wednes|thurs|fri|satur|sun)day|will be joined by|in person|pre-recorded",
    re.I,
)
_SENTENCE_END = re.compile(r"(?<=[.!?…])[\"'”’)]?\s+(?=[A-Z0-9\"“‘(])")


def make_blurb(raw: str | None) -> str | None:
    """A couple of clean lines from a venue's description: HTML and housekeeping
    (prices, booking info, credits) removed, cut at a sentence end to <= BLURB_MAX chars."""
    if not raw:
        return None
    t = re.sub(r"<(?:br|/p|/div|/li|/h\d)[^>]*>", "\n", raw, flags=re.I)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t)).replace("\xa0", " ")
    t = re.sub(r"\[/?embed\].*?(?:\[/embed\]|$)", " ", t, flags=re.I)
    lines = []
    for line in re.split(r"\n+", t):
        line = re.sub(r"\s+", " ", line).strip(" -–•*|")
        if len(line) < 25 or _BOILERPLATE.search(line):
            continue
        letters = [c for c in line if c.isalpha()]
        if letters and sum(c.isupper() for c in letters) / len(letters) > 0.6:
            continue  # SHOUTY headings
        lines.append(line)
    text = " ".join(lines).strip()
    if re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", text):
        return None  # generated "<Artist> at <Venue> at 2026-11-18T19:00" text, not a description
    # Drop a leading "TITLE:" / date prefix ("25th October 2026. MALIN PETTERSEN: ...").
    text = re.sub(r"^\d{1,2}(?:st|nd|rd|th)?\s+\w+\s+\d{4}\.\s*", "", text)
    text = re.sub(r"^[A-Z][A-Z0-9 '&!.,-]{2,60}:\s+", "", text)
    sentences = _SENTENCE_END.split(text)
    if len(sentences) > 1 and text.rstrip().endswith(("…", "...")):
        sentences = sentences[:-1]  # the source cut the last sentence off
    # Sentences about this particular screening rather than the film/show.
    sentences = [x for x in sentences if not _SCREENING_NOTE.search(x)]
    text = " ".join(sentences)
    if len(text) < 40 or len(text.split()) < 8:
        return None
    out = ""
    for sentence in sentences:
        candidate = f"{out} {sentence}".strip()
        if len(candidate) > BLURB_MAX:
            break
        out = candidate
    if not out:  # first sentence alone is too long: cut at a word boundary
        out = text[: BLURB_MAX - 1].rsplit(" ", 1)[0].rstrip(",;:—–- ") + "…"
    return out


def blurb_score(text: str) -> float:
    """Higher is better: sentence-like, 80-280 chars, few capitals."""
    score = min(len(text), BLURB_MAX) / BLURB_MAX
    if text.endswith((".", "!", "?", "”", '"')):
        score += 0.5
    if len(text) < 80:
        score -= 0.5
    caps = sum(c.isupper() for c in text) / max(1, sum(c.isalpha() for c in text))
    return score - caps


def page_description(soup) -> str | None:
    """A page's own summary: og:description, else meta description."""
    for attrs in ({"property": "og:description"}, {"name": "description"}, {"name": "twitter:description"}):
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content", "").strip():
            return tag["content"].strip()
    return None
