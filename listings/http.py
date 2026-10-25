"""A polite HTTP client shared by all venues.

- Identifies itself with a clear User-Agent and contact address.
- Checks robots.txt before every request and refuses disallowed URLs.
- Waits between requests to the same host (honouring Crawl-delay if larger).
- Caches responses on disk so repeated runs don't re-hit the source.
- Recognises bot-challenge pages (e.g. Cloudflare) and stops instead of retrying.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.robotparser
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

import requests

USER_AGENT = (
    "LondonListingsBot/0.1 "
    "(personal non-commercial project; +https://github.com/kabirhusain/london-listings)"
)
DEFAULT_DELAY_SECONDS = 3.0
DEFAULT_CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache" / "http"


class FetchError(Exception):
    """A request failed or returned something unusable."""


class RobotsDisallowed(FetchError):
    """robots.txt says we may not fetch this URL."""


class BlockedByChallenge(FetchError):
    """The site served a bot challenge. We do not try to get past these."""


@dataclass
class Response:
    url: str  # final URL after redirects
    status: int
    text: str
    from_cache: bool
    redirects: list[str] = field(default_factory=list)  # URLs we were redirected through

    def json(self):
        return json.loads(self.text)


class PoliteClient:
    def __init__(
        self,
        user_agent: str = USER_AGENT,
        delay_seconds: float = DEFAULT_DELAY_SECONDS,
        cache_dir: Path | None = DEFAULT_CACHE_DIR,
        cache_ttl_seconds: float = 6 * 3600,
        timeout_seconds: float = 60,
    ):
        self.user_agent = user_agent
        self.delay_seconds = delay_seconds
        self.cache_dir = cache_dir
        self.cache_ttl_seconds = cache_ttl_seconds
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.headers["User-Agent"] = user_agent
        self._robots: dict[str, urllib.robotparser.RobotFileParser] = {}
        self._last_request_at: dict[str, float] = {}
        self._host_delay: dict[str, float] = {}  # from robots.txt Crawl-delay

    # -- public API ---------------------------------------------------------

    def get(self, url: str, use_cache: bool = True, max_age: float | None = None) -> Response:
        """GET a URL. `max_age` overrides the cache lifetime (seconds), e.g. a week
        for event detail pages that rarely change."""
        cached = self._read_cache(url, max_age) if use_cache else None
        if cached is not None:
            return cached

        self._check_robots(url)
        resp = self._throttled_get(url)
        if _looks_like_challenge(resp):
            raise BlockedByChallenge(
                f"{urlsplit(url).netloc} served a bot challenge (HTTP {resp.status_code}). "
                "Not attempting to bypass it."
            )
        if resp.status_code != 200:
            raise FetchError(f"HTTP {resp.status_code} for {url}")

        result = Response(
            url=resp.url,
            status=resp.status_code,
            text=resp.text,
            from_cache=False,
            redirects=[h.headers.get("location", "") for h in resp.history],
        )
        self._write_cache(url, result)
        return result

    def get_json(self, url: str, use_cache: bool = True):
        resp = self.get(url, use_cache=use_cache)
        try:
            return resp.json(), resp
        except json.JSONDecodeError as e:
            raise FetchError(f"Expected JSON from {url}, got: {resp.text[:200]!r}") from e

    # -- robots.txt ---------------------------------------------------------

    def _check_robots(self, url: str) -> None:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        parser = self._robots.get(origin)
        if parser is None:
            parser = urllib.robotparser.RobotFileParser()
            robots_url = f"{origin}/robots.txt"
            resp = self._throttled_get(robots_url)
            if resp.status_code == 200 and not _looks_like_challenge(resp):
                parser.parse(resp.text.splitlines())
            elif resp.status_code in (401, 403) or _looks_like_challenge(resp):
                # Can't read the rules, so assume we're not welcome.
                parser.parse(["User-agent: *", "Disallow: /"])
            else:
                # 404 etc. means no restrictions.
                parser.parse([])
            self._robots[origin] = parser
        if not parser.can_fetch(self.user_agent, url):
            raise RobotsDisallowed(f"robots.txt disallows {url}")
        crawl_delay = parser.crawl_delay(self.user_agent)
        if crawl_delay:
            self._host_delay[parts.netloc] = float(crawl_delay)

    # -- throttling ---------------------------------------------------------

    def _throttled_get(self, url: str) -> requests.Response:
        host = urlsplit(url).netloc
        last = self._last_request_at.get(host)
        if last is not None:
            delay = max(self.delay_seconds, self._host_delay.get(host, 0.0))
            wait = delay - (time.monotonic() - last)
            if wait > 0:
                time.sleep(wait)
        try:
            try:
                return self.session.get(url, timeout=self.timeout_seconds)
            except requests.ConnectionError:
                # Some servers drop idle keep-alive connections after a few
                # seconds, i.e. right around our delay. Retry once on a new one.
                self.session.close()
                return self.session.get(url, timeout=self.timeout_seconds)
        except requests.RequestException as e:
            raise FetchError(f"Request to {url} failed: {e}") from e
        finally:
            self._last_request_at[host] = time.monotonic()

    # -- cache --------------------------------------------------------------

    def _cache_path(self, url: str) -> Path | None:
        if self.cache_dir is None:
            return None
        return self.cache_dir / (hashlib.sha256(url.encode()).hexdigest()[:32] + ".json")

    def _read_cache(self, url: str, max_age: float | None = None) -> Response | None:
        path = self._cache_path(url)
        if path is None or not path.exists():
            return None
        if time.time() - path.stat().st_mtime > (max_age if max_age is not None else self.cache_ttl_seconds):
            return None
        data = json.loads(path.read_text())
        return Response(**{**data, "from_cache": True})

    def _write_cache(self, url: str, resp: Response) -> None:
        path = self._cache_path(url)
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({k: v for k, v in asdict(resp).items() if k != "from_cache"}))


def _looks_like_challenge(resp: requests.Response) -> bool:
    if resp.headers.get("cf-mitigated") == "challenge":
        return True
    # Imperva Incapsula serves its block/challenge page with HTTP 200.
    if "_Incapsula_Resource" in resp.text[:3000] or "Incapsula incident ID" in resp.text[:3000]:
        return True
    if resp.status_code in (403, 429, 503):
        head = resp.text[:3000]
        return any(
            marker in head
            for marker in ("Just a moment...", "Attention Required!", "_cf_chl_opt", "cf-browser-verification")
        )
    return False
