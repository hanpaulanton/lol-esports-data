"""PHASE 18-3-C evidence acquisition: Data:2026 Season World Championship/Main Event.

Single permitted GET (handoff section 6: 1-2 carefully targeted requests).
Page name comes from the PHASE 18-3-B request #11 discovery
(raw/leaguepedia/phase18_3b_fetch_metadata.json): Data-namespace pages under
"2026 Season World Championship" are exactly "/Main Event" and "/Play-In".
No discovery requests are made here; on failure we STOP per handoff 19/22.
"""

from __future__ import annotations

import datetime
import json
import pathlib
import sys
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]

RAW_DIR = ROOT / "raw" / "leaguepedia"
META_PATH = RAW_DIR / "phase18_3c_fetch_metadata.json"

UA = "LoLEsportsFanDataCollector/0.1 (unofficial fan project; personal non-commercial)"
API = "https://lol.fandom.com/api.php"
TITLE = "Data:2026 Season World Championship/Main Event"


def main() -> int:
    fetched_at_utc = datetime.datetime.now(datetime.timezone.utc).isoformat(
        timespec="seconds").replace("+00:00", "Z")

    params = {
        "action": "query",
        "titles": TITLE,
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "format": "json",
        "formatversion": "2",
    }
    url = API + "?" + urllib.parse.urlencode(params)

    entry = {
        "phase": "PHASE 18-3-C",
        "fetchedAt": fetched_at_utc,
        "sourceUrl": url,
        "pageTitle": TITLE,
        "requestPurpose": "PHASE 18-3-C evidence acquisition request #1 (known-team scheduled MatchSchedule)",
        "userAgent": UA,
        "networkRequestCount": 1,
        "retries": 0,
    }

    request = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status = response.status
            body = response.read().decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        entry["outcome"] = f"FETCH-FAILED: {exc}"
        entry["httpStatus"] = None
        META_PATH.write_text(json.dumps(entry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"FETCH-FAILED: {exc}", file=sys.stderr)
        return 1

    entry["httpStatus"] = status
    json_path = RAW_DIR / "page_Data_2026 Season World Championship_Main Event_wikitext.json"
    json_path.write_text(body, encoding="utf-8")

    payload = json.loads(body)
    page = payload["query"]["pages"][0]
    if "revisions" not in page:
        entry["outcome"] = f"PAGE-EMPTY: title={page.get('title')!r} has no revisions — nothing usable saved"
        META_PATH.write_text(json.dumps(entry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(entry["outcome"])
        return 1

    wikitext = page["revisions"][0]["slots"]["main"]["content"]
    wikitext_path = RAW_DIR / "page_Data_2026 Season World Championship_Main Event.wikitext"
    wikitext_path.write_text(wikitext, encoding="utf-8")
    entry["outcome"] = (
        f"HTTP 200, saved {json_path.name} + {wikitext_path.name}; "
        f"wikitext_len={len(wikitext)} title={page.get('title')!r}"
    )
    META_PATH.write_text(json.dumps(entry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"FETCH-OK status={status} wikitext_len={len(wikitext)} title={page.get('title')!r} fetchedAt={fetched_at_utc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
