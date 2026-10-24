"""Write a small index.html for the GitHub Pages site from status.json.

    python scripts/20261024_make_index.py site
"""

import html
import json
import sys
from pathlib import Path

site = Path(sys.argv[1] if len(sys.argv) > 1 else "site")
status = json.loads((site / "status.json").read_text())
listings = json.loads((site / "listings.json").read_text())

rows = "\n".join(
    f"<tr class='{html.escape(v['status'] or '')}'><td>{html.escape(v['name'])}</td>"
    f"<td>{html.escape(v['status'] or '')}</td><td>{v['published']}</td>"
    f"<td>{html.escape((v['last_success'] or '—')[:16].replace('T', ' '))}</td>"
    f"<td>{html.escape((v['error'] or '')[:120])}</td></tr>"
    for v in status["venues"]
)
s = status["summary"]
page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>London listings</title>
<style>
:root {{ --bg:#fff; --fg:#1a1a1a; --muted:#666; --line:#e3e3e3; --bad:#b3261e; --warn:#8a5a00; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#141414; --fg:#eee; --muted:#aaa; --line:#333; --bad:#ff8a80; --warn:#ffd180; }} }}
body {{ background:var(--bg); color:var(--fg); font:15px/1.5 system-ui, sans-serif; margin:0 auto; max-width:960px; padding:24px 16px; }}
table {{ border-collapse:collapse; width:100%; }} td, th {{ border-bottom:1px solid var(--line); padding:6px 8px; text-align:left; vertical-align:top; }}
.failed td {{ color:var(--bad); }} .stale td {{ color:var(--warn); }} .muted {{ color:var(--muted); }}
.wrap {{ overflow-x:auto; }}
</style></head><body>
<h1>London cinema &amp; music listings</h1>
<p><a href="listings.json">listings.json</a> ({len(listings['showings'])} showings) ·
<a href="status.json">status.json</a> · generated {html.escape(status['generated_at'][:16].replace('T', ' '))} (London)</p>
<p class="muted">{s['ok']} venues ok, {s['stale']} stale (last good data reused), {s['failed']} failed, {s['manual']} manual only.</p>
<div class="wrap"><table><thead><tr><th>Venue</th><th>Status</th><th>Listings</th><th>Last success</th><th>Error</th></tr></thead>
<tbody>
{rows}
</tbody></table></div>
<p class="muted">Some data from <a href="https://clusterflick.com">Clusterflick</a> (CC BY 4.0), modified.</p>
</body></html>
"""
(site / "index.html").write_text(page)
