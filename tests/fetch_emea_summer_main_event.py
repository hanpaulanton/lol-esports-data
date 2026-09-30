"""PHASE 18-3-D-EMEA: single-request evidence acquisition from
Data:EMEA Masters/2026 Season/Summer Main Event (Leaguepedia Data namespace).

One HTTP GET via the already-established action=query path. Saves the raw
response verbatim and the extracted wikitext as NEW fixtures (previous
PHASE 18-3-B/C fixtures are not overwritten), records metadata, then prints
a quick classification of MatchSchedule rows. No retries, no cargoquery,
no discovery requests."""

from __future__ import annotations

import datetime
import json
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.series_score import iter_series_with_games  # noqa: E402

UA = "LoLEsportsFanDataCollector/0.1 (unofficial fan project; personal non-commercial)"
API = "https://lol.fandom.com/api.php"
TITLE = "Data:EMEA Masters/2026 Season/Summer Main Event"
RAW_DIR = ROOT / "raw" / "leaguepedia"
FIXTURE_STEM = "page_EMEA_Masters_2026_Summer_Main_Event"


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
        (RAW_DIR / f"{FIXTURE_STEM}_fetch_error.txt").write_text(f"{url}\n{exc}", encoding="utf-8")
        print(f"FETCH-FAILED: {exc}", file=sys.stderr)
        return 1

    (RAW_DIR / f"{FIXTURE_STEM}_wikitext.json").write_text(body, encoding="utf-8")

    payload = json.loads(body)
    page = payload["query"]["pages"][0]
    if "revisions" not in page:
        print(f"PAGE-MISSING: {page.get('title')!r} (no revisions)")
        return 1
    wikitext = page["revisions"][0]["slots"]["main"]["content"]
    (RAW_DIR / f"{FIXTURE_STEM}.wikitext").write_text(wikitext, encoding="utf-8")

    (RAW_DIR / "phase18_3d_emea_fetch_metadata.json").write_text(
        json.dumps(
            {
                "phase": "PHASE 18-3-D-EMEA",
                "fetchedAt": fetched_at_utc,
                "sourceUrl": url,
                "pageTitle": page.get("title", TITLE),
                "requestPurpose": "PHASE 18-3-D-EMEA evidence acquisition (known-team scheduled MatchSchedule, single allowed request)",
                "userAgent": UA,
                "networkRequestCount": 1,
                "retries": 0,
                "httpStatus": status,
                "outcome": f"HTTP 200, wikitext_len={len(wikitext)}",
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"FETCH-OK status={status} wikitext_len={len(wikitext)} title={page.get('title')!r} fetched_at={fetched_at_utc}")

    # Quick classification only (full analysis happens offline afterwards).
    for index, (context, args, games) in enumerate(iter_series_with_games(wikitext), 1):
        t1 = (args.get("team1") or "").strip()
        t2 = (args.get("team2") or "").strip()
        winner = (args.get("winner") or "").strip()
        s1 = (args.get("team1score") or "").strip()
        s2 = (args.get("team2score") or "").strip()
        date = (args.get("date") or "").strip()
        time_ = (args.get("time") or "").strip()
        tz = (args.get("timezone") or "").strip()
        dst = (args.get("dst") or "").strip()
        rowbo = (args.get("bestof") or "").strip()
        rpgid_filled = sum(1 for _k, ga in games if (ga.get("riot_platform_game_id") or "").strip())
        kind = "KNOWN-TEAM" if (t1 and t2) else "empty-slots"
        state = "no-result" if not (winner or s1 or s2) else "has-result"
        print(f"{index:02d} [{kind}/{state}] tab={context.get('tab')!r} startbo={context.get('bestof')!r} rowbo={rowbo!r} "
              f"t1={t1!r} t2={t2!r} w={winner!r} s={s1}-{s2} {date} {time_} {tz} dst={dst!r} games={len(games)} rpgid={rpgid_filled}/{len(games)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
