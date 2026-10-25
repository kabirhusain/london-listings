"""Command line entry point.

    python -m listings collect [--venue SLUG ...] [-o listings.json] [--previous PATH_OR_URL]
    python -m listings probe URL
    python -m listings list-venues
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

from listings.http import USER_AGENT, PoliteClient
from listings.manual import DEFAULT_DIR as MANUAL_DIR, load_manual
from listings.model import blurb_key, clean_info_url, is_upcoming, london_iso, upgrade_showing, validate_listings
from listings.text import blurb_score, make_blurb, match_key
from listings.venues import all_venues

log = logging.getLogger("listings")


def collect(
    venue_slugs: list[str] | None,
    client: PoliteClient | None = None,
    previous: dict | None = None,
    manual_dir: Path | None = None,
    local: list[dict] | None = None,
) -> tuple[dict, list[str]]:
    """Fetch the given venues (default: all) and merge them into one document.

    If a venue fails, its upcoming showings from `previous` (the last published
    listings.json) are carried over and its source entry is marked "stale".
    Hand-entered showings from `manual_dir` are added (past ones dropped);
    where they duplicate a scraped showing, the scraped one wins.
    `local` are listings.json documents from runs on another machine (for
    venues that block this one): when a venue fails here, the freshest of
    `previous` and `local` is used.
    Returns (document, error messages).
    """
    client = client or PoliteClient()
    previous = previous or {}
    venues = all_venues()
    now = datetime.now(timezone.utc)
    now_iso = london_iso(now)

    showings, sources, errors = [], [], []
    blurb_candidates: dict[str, list[str]] = {}
    for slug in venue_slugs or sorted(venues):
        venue = venues[slug]
        try:
            fetched = venue.fetch(client)
            venue_showings = [s.to_dict() for s in fetched]
            # A description a venue uses for several different titles is site
            # boilerplate (e.g. a generic og:description), not a blurb.
            titles_per_text: dict[str, set[str]] = {}
            venue_blurbs = []
            for obj, d in zip(fetched, venue_showings):
                text = make_blurb(obj.description)
                if text and not _mostly_title(text, d["title"]):
                    titles_per_text.setdefault(text, set()).add(blurb_key(d))
                    venue_blurbs.append((blurb_key(d), text))
            for key, text in venue_blurbs:
                if len(titles_per_text[text]) <= 2:
                    blurb_candidates.setdefault(key, []).append(text)
            # Check this venue on its own, so one bad record fails only its venue.
            validate_listings({"generated_at": london_iso(now), "showings": venue_showings})
        except Exception as e:  # one broken venue mustn't sink the rest
            message = f"{slug}: {type(e).__name__}: {e}"
            errors.append(message)
            log.error(message)
            fallback, prev = _freshest_fallback(slug, [previous, *(local or [])])
            carried = [
                upgrade_showing(s) for s in fallback.get("showings", [])
                if s["id"].startswith(f"{slug}:") and ":manual-" not in s["id"]  # manual ones are reloaded below
                and is_upcoming(s, now)
            ]
            sources.append({
                "venue": slug,
                "status": "stale" if carried else "failed",
                "error": message,
                "fetched_at": prev.get("fetched_at"),
                "source": prev.get("source", venue.source_description),
                **({"attribution": prev["attribution"]} if "attribution" in prev else {}),
                "showings": len(carried),
            })
            showings.extend(carried)
            continue
        showings.extend(venue_showings)
        sources.append({
            **venue.source_info(),
            "status": "ok",
            "fetched_at": now_iso,
            "showings": len(venue_showings),
        })

    if manual_dir is not None:
        manual_venues, manual_errors = load_manual(manual_dir, venues)
        for message in manual_errors:
            errors.append(message)
            log.error(message)
        for mv in manual_venues:
            if venue_slugs and mv.slug not in venue_slugs:
                continue
            showings.extend(mv.showings)
            sources.append({
                "venue": mv.slug,
                "status": "manual",
                "source": mv.file,
                "fetched_at": now_iso,
                "showings": len(mv.showings),
                "skipped_past": mv.skipped_past,
            })

    merged = merge(showings)
    doc = {
        "generated_at": now_iso,
        "sources": sources,
        "blurbs": pick_blurbs(merged, blurb_candidates, previous.get("blurbs", {})),
        "showings": merged,
    }
    validate_listings(doc)
    return doc, errors


def _mostly_title(text: str, title: str) -> bool:
    """True for "descriptions" that just repeat the title (e.g. "Swan Lake - Sadler's Wells Theatre")."""
    words = set(match_key(text).split())
    return bool(words) and len(words & set(match_key(title).split())) / len(words) >= 0.5


def pick_blurbs(showings: list[dict], candidates: dict[str, list[str]], previous: dict[str, str]) -> dict[str, str]:
    """One blurb per title that has showings: the best-scoring candidate from
    today's run, else yesterday's blurb (e.g. if that venue failed today)."""
    out = {}
    for key in sorted({blurb_key(s) for s in showings}):
        if candidates.get(key):
            out[key] = max(candidates[key], key=blurb_score)
        elif key in previous:
            out[key] = previous[key]
    return out


def _freshest_fallback(slug: str, docs: list[dict]) -> tuple[dict, dict]:
    """Of several earlier listings documents, the one with the most recent
    successful data for `slug`. Returns (document, its source entry)."""
    best_doc, best_src = {}, {}
    for doc in docs:
        for src in (doc or {}).get("sources", []):
            if src.get("venue") == slug and src.get("status") != "manual" and src.get("fetched_at"):
                if (src["fetched_at"] or "") > (best_src.get("fetched_at") or ""):
                    best_doc, best_src = doc, src
    return best_doc, best_src


def merge(showings: list[dict]) -> list[dict]:
    """Deduplicate and sort by start time.

    Duplicates are the same id, or the same venue + title + start (which can
    happen if a source lists one performance twice under different ids).
    """
    seen_ids, seen_keys, out = set(), set(), []
    for s in (clean_info_url(upgrade_showing(x)) for x in showings):  # also fills match_key on carried-over/manual entries
        key = (s["venue"], s["match_key"], s["start"])
        if s["id"] in seen_ids or key in seen_keys:
            continue
        seen_ids.add(s["id"])
        seen_keys.add(key)
        out.append(s)
    out.sort(key=lambda s: (datetime.fromisoformat(s["start"]), s["venue"], s["title"]))
    return out


def build_status(doc: dict, previous_status: dict | None = None) -> dict:
    """One entry per venue: did today's run work, when did it last work, how many listings.

    `last_success` survives failed days by reading the previously published status.json.
    """
    prev = {v["venue"]: v for v in (previous_status or {}).get("venues", [])}
    names = {slug: v.name for slug, v in all_venues().items()}
    by_venue: dict[str, dict] = {}
    for src in doc["sources"]:
        slug = src["venue"]
        entry = by_venue.setdefault(slug, {
            "venue": slug,
            "name": names.get(slug, slug),
            "status": None,
            "last_success": prev.get(slug, {}).get("last_success"),
            "listings": 0,
            "manual_listings": 0,
            "error": None,
            "source": None,
        })
        if src["status"] == "manual":
            entry["manual_listings"] += src["showings"]
            entry["status"] = entry["status"] or "manual"
            entry["source"] = entry["source"] or src.get("source")
            if entry["name"] == slug:  # manual-only venue: take the name from its showings
                entry["name"] = next((s["venue"] for s in doc["showings"] if s["id"].startswith(f"{slug}:")), slug)
            continue
        entry["status"] = src["status"]
        entry["listings"] = src["showings"]
        entry["source"] = src.get("source")
        entry["error"] = src.get("error")
        if src["status"] == "ok":
            entry["last_success"] = src["fetched_at"]
        elif src.get("fetched_at") and (entry["last_success"] or "") < src["fetched_at"]:
            entry["last_success"] = src["fetched_at"]
    counts = {}
    for s in doc["showings"]:
        counts[s["id"].split(":", 1)[0]] = counts.get(s["id"].split(":", 1)[0], 0) + 1
    for slug, entry in by_venue.items():
        entry["published"] = counts.get(slug, 0)  # after merging and de-duplication
    venues = sorted(by_venue.values(), key=lambda v: v["name"].lower())
    summary = {k: sum(1 for v in venues if v["status"] == k) for k in ("ok", "stale", "failed", "manual")}
    return {"generated_at": doc["generated_at"], "summary": summary, "venues": venues}


def load_previous(location: str | None) -> dict:
    """Load the last published listings.json from a path or URL. Missing is fine."""
    if not location:
        return {}
    try:
        if location.startswith(("http://", "https://")):
            resp = requests.get(location, headers={"User-Agent": USER_AGENT}, timeout=30)
            if resp.status_code == 404:
                return {}
            resp.raise_for_status()
            return resp.json()
        path = Path(location)
        return json.loads(path.read_text()) if path.exists() else {}
    except Exception as e:
        log.warning("couldn't load previous listings from %s: %s", location, e)
        return {}


class _GitHubAnnotations(logging.Handler):
    """Surface warnings/errors as annotations on the GitHub Actions run."""

    def emit(self, record):
        level = "error" if record.levelno >= logging.ERROR else "warning"
        print(f"::{level}::{record.getMessage()}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if os.environ.get("GITHUB_ACTIONS") == "true":
        handler = _GitHubAnnotations(level=logging.WARNING)
        log.addHandler(handler)

    parser = argparse.ArgumentParser(prog="listings")
    sub = parser.add_subparsers(dest="command", required=True)
    p_collect = sub.add_parser("collect", help="fetch listings and write JSON")
    p_collect.add_argument("--venue", action="append", help="venue slug (repeatable); default all")
    p_collect.add_argument("-o", "--output", default="listings.json")
    p_collect.add_argument(
        "--previous",
        help="last published listings.json (path or URL), used for venues that fail; default: the output file",
    )
    p_collect.add_argument("--no-cache", action="store_true", help="ignore the on-disk HTTP cache")
    p_collect.add_argument("--manual-dir", default=str(MANUAL_DIR), help="folder of hand-entered venue files")
    p_collect.add_argument("--status", help="also write status.json here")
    p_collect.add_argument("--previous-status", help="last published status.json (path or URL); default: the --status file")
    p_collect.add_argument(
        "--local", action="append", default=[],
        help="listings.json written by a local run (path or URL); used for venues that fail here, if newer",
    )
    p_check = sub.add_parser("check-manual", help="validate the manual/ files without fetching anything")
    p_check.add_argument("--manual-dir", default=str(MANUAL_DIR))
    p_probe = sub.add_parser("probe", help="look for structured listing sources on a page")
    p_probe.add_argument("url")
    sub.add_parser("list-venues")
    args = parser.parse_args(argv)

    if args.command == "list-venues":
        for slug, venue in sorted(all_venues().items()):
            print(f"{slug:22} {venue.name:24} {venue.source_description}")
        return 0

    if args.command == "check-manual":
        venues, errors = load_manual(Path(args.manual_dir), all_venues())
        for v in venues:
            print(f"OK    {v.file}: {v.name} ({v.slug}), {len(v.showings)} upcoming, {v.skipped_past} past (ignored)")
        for e in errors:
            print(f"ERROR {e}")
        return 1 if errors else 0

    if args.command == "probe":
        from listings.probe import probe
        print(json.dumps(probe(args.url), indent=2))
        return 0

    unknown = set(args.venue or []) - set(all_venues())
    if unknown:
        parser.error(f"unknown venue(s): {', '.join(sorted(unknown))}")
    client = PoliteClient(cache_dir=None) if args.no_cache else PoliteClient()
    previous = load_previous(args.previous or args.output)
    local = [load_previous(x) for x in args.local]
    doc, errors = collect(args.venue, client, previous, Path(args.manual_dir), local=local)

    if not doc["showings"]:
        log.error("No showings collected; %s left unchanged.", args.output)
        return 1
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(out)
    if args.status:
        status = build_status(doc, load_previous(args.previous_status or args.status))
        Path(args.status).parent.mkdir(parents=True, exist_ok=True)
        Path(args.status).write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n")
    for s in doc["sources"]:
        log.info("%-22s %-6s %4d showings", s["venue"], s["status"], s["showings"])
    log.info("Wrote %d showings to %s (%d venue error(s))", len(doc["showings"]), out, len(errors))
    # Partial failure still publishes; the errors are logged above.
    return 0


if __name__ == "__main__":
    sys.exit(main())
