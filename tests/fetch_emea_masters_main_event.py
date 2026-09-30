"""PHASE 18-3-D-EMEA request #1 (single allowed request): retrieve
Data:EMEA Masters/2026 Season/Summer Main Event.

One HTTP GET via the already-approved action=query path (same conventions as
PHASE 18-3-B/18-3-C: UA, no retries, raw response preserved verbatim).
Purpose: find a genuinely upcoming scheduled MatchSchedule with populated
team1/team2 (Q1) and check riot_platform_game_id preassignment (Q2)."""

from __future__ import annotations

import datetime
import json
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]

UA = "LoLEsportsFanDataCollector/0.1 (unofficial fan project; personal non-commercial)"
API = "https://lol.fandom.com/api.php"
TITLE = "Data:EMEA Masters/2026 Season/Summer Main Event"
RAW_DIR = ROOT / "raw" / "leaguepedia"


def main() -> int:
    params = {
        "action": "query",
        "titles": TITLE,
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "format": "json",
        "formatversion": "2",
    }
    url = API + "?" + "&".join(f"{k}={urllib.request.quote(v)}" for k, v in params.items())
    fetched_at_utc = (
        datetime.datetime.now(datetime.timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status = response.status
            body = response.read().decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        print(f"FETCH-FAILED: {exc}", file=sys.stderr)
        return 1

    json_path = RAW_DIR / "page_EMEA_Masters_2026_Summer_Main_Event_wikitext.json"
    json_path.write_text(body, encoding="utf-8")

    payload = json.loads(body)
    page = payload["query"]["pages"][0]
    if "revisions" not in page:
        print(f"PAGE-MISSING: {page.get('title')!r} (no revisions)")
        return 1
    wikitext = page["revisions"][0]["slots"]["main"]["content"]
    wikitext_path = RAW_DIR / "page_EMEA_Masters_2026_Summer_Main_Event.wikitext"
    wikitext_path.write_text(wikitext, encoding="utf-8")

    meta_path = RAW_DIR / "phase18_3d_emea_fetch_metadata.json"
    meta_path.write_text(
        json.dumps(
            {
                "phase": "PHASE 18-3-D-EMEA",
                "fetchedAt": fetched_at_utc,
                "sourceUrl": url,
                "pageTitle": page.get("title", TITLE),
                "requestPurpose": "PHASE 18-3-D-EMEA request #1 (single allowed request): known-team scheduled MatchSchedule evidence from EMEA Masters 2026 Summer Main Event",
                "userAgent": UA,
                "networkRequestCount": 1,
                "retries": 0,
                "httpStatus": status,
                "outcome": f"HTTP 200, saved page_EMEA_Masters_2026_Summer_Main_Event_wikitext.json + .wikitext; wikitext_len={len(wikitext)}",
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"FETCH-OK status={status} wikitext_len={len(wikitext)} title={page.get('title')!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
