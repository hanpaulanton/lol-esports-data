"""PHASE 18-3-C request #2 (discovery): enumerate all Data-namespace pages
prefixed "2026 Season" to verify whether any Riot-event Data page exists that
could contain a known-team scheduled MatchSchedule (the two known pages —
Worlds Play-In and Main Event — both have empty team slots).

One HTTP GET via the already-approved action=query&list=allpages path (same
pattern as PHASE 18-3-B requests #5/#7/#11, all HTTP 200). No retries, no
other requests, no cargoquery. Saves the raw response verbatim plus a
metadata record following the repository collection conventions."""

from __future__ import annotations

import datetime
import json
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]

UA = "LoLEsportsFanDataCollector/0.1 (unofficial fan project; personal non-commercial)"
API = "https://lol.fandom.com/api.php"
RAW_DIR = ROOT / "raw" / "leaguepedia"

PARAMS = {
    "action": "query",
    "list": "allpages",
    "apprefix": "2026 Season",
    "apnamespace": "10008",
    "aplimit": "500",
    "format": "json",
    "formatversion": "2",
}


def main() -> int:
    url = API + "?" + "&".join(f"{k}={urllib.request.quote(v)}" for k, v in PARAMS.items())
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

    raw_path = RAW_DIR / "allpages_2026_season_data_namespace.json"
    raw_path.write_text(body, encoding="utf-8")

    payload = json.loads(body)
    pages = [p["title"] for p in payload.get("query", {}).get("allpages", [])]
    print(f"FETCH-OK status={status} pages={len(pages)}")
    for title in pages:
        print(f"  {title}")

    meta_path = RAW_DIR / "phase18_3c_discovery_metadata.json"
    meta_path.write_text(
        json.dumps(
            {
                "phase": "PHASE 18-3-C",
                "fetchedAt": fetched_at_utc,
                "sourceUrl": url,
                "pageTitle": None,
                "requestPurpose": "PHASE 18-3-C request #2 (discovery): enumerate Data pages prefixed '2026 Season' to check for any event page beyond World Championship/{Play-In,Main Event} that could hold a known-team scheduled match",
                "userAgent": UA,
                "networkRequestCount": 1,
                "retries": 0,
                "httpStatus": status,
                "outcome": f"HTTP 200, {len(pages)} Data pages found; raw response saved to allpages_2026_season_data_namespace.json",
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
