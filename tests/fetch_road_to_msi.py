"""PHASE 18-3-A request #2 (final): Data:LCK/2026 Season/Road to MSI."""

from __future__ import annotations

import datetime
import json
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

RAW_DIR = ROOT / "raw" / "leaguepedia"

from lib.leaguepedia_parser import find_templates, find_nested_by_name  # noqa: E402

UA = "LoLEsportsFanDataCollector/0.1 (unofficial fan project; personal non-commercial)"
API = "https://lol.fandom.com/api.php"
TITLE = "Data:LCK/2026 Season/Road to MSI"
OUT_DIR = ROOT / "phase18-3a-test"

def to_int(value: str | None):
    value = (value or "").strip()
    return int(value) if value.isdigit() else None

def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
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

    fetched_at_utc = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    request_count = 0
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status = response.status
            body = response.read().decode("utf-8", errors="replace")
            request_count = 1
    except Exception as exc:  # noqa: BLE001
        (OUT_DIR / "fetch-error.txt").write_text(f"{url}\n{exc}", encoding="utf-8")
        print(f"FETCH-FAILED: {exc}", file=sys.stderr)
        return 1

    json_path = RAW_DIR / "page_data_lck_road_to_msi_scheduled_wikitext.json"
    json_path.write_text(body, encoding="utf-8")

    payload = json.loads(body)
    page = payload["query"]["pages"][0]
    if "revisions" not in page:
        print(f"PAGE-MISSING: {page.get('title')!r} (no revisions)")
        return 1
    wikitext = page["revisions"][0]["slots"]["main"]["content"]
    wikitext_path = RAW_DIR / "page_data_lck_road_to_msi_scheduled.wikitext"
    wikitext_path.write_text(wikitext, encoding="utf-8")

    (RAW_DIR / "scheduled_fetch_metadata.json").write_text(
        json.dumps({
            "fetchedAt": fetched_at_utc,
            "sourceUrl": url,
            "httpStatus": status,
            "pageTitle": page.get("title", TITLE),
            "requestPurpose": "PHASE 18-3-A evidence acquisition request #2 (final allowed GET)",
            "userAgent": UA,
            "networkRequestCount": request_count,
            "retries": 0,
        }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(f"FETCH-OK status={status} wikitext_len={len(wikitext)} title={page.get('title')!r}")

    series: list[dict] = []
    starts: list[dict] = []
    context: dict = {}
    for t in find_templates(wikitext):
        if t.name == "MatchSchedule/Start":
            context = {
                "tab": (t.args.named.get("tab") or "").strip(),
                "bestof": (t.args.named.get("bestof") or "").strip(),
                "shownname": (t.args.named.get("shownname") or "").strip(),
            }
            starts.append({"context": context, "start": t.start})
        elif t.name == "MatchSchedule":
            games = []
            for arg_key, arg_value in t.args.named.items():
                if arg_key.lower().startswith("game"):
                    for g in find_nested_by_name(arg_value, "MatchSchedule/Game"):
                        games.append({"argKey": arg_key, "args": {k: v.strip() for k, v in g.args.named.items()}})
            series.append({
                "index": len(series) + 1,
                "context": context,
                "args": {k: v.strip() for k, v in t.args.named.items()},
                "games": games,
                "start": t.start,
            })

    completed = 0
    candidates = 0
    rows = []
    for s in series:
        args = s["args"]
        winner = to_int(args.get("winner"))
        s1 = to_int(args.get("team1score"))
        s2 = to_int(args.get("team2score"))
        if winner is not None and s1 is not None and s2 is not None:
            completed += 1
            classification = "COMPLETED"
        else:
            candidates += 1
            classification = "SCHEDULED_CANDIDATE"
        rows.append({
            "classification": classification,
            "contextTab": s["context"].get("tab"),
            "contextBestOf": s["context"].get("bestof"),
            "team1": args.get("team1"),
            "team2": args.get("team2"),
            "team1score": args.get("team1score"),
            "team2score": args.get("team2score"),
            "winner": args.get("winner"),
            "date": args.get("date"),
            "time": args.get("time"),
            "timezone": args.get("timezone"),
            "dst": args.get("dst"),
            "gameCount": len(s["games"]),
            "gameRpgids": [g["args"].get("riot_platform_game_id", "") for g in s["games"]],
            "allArgs": args,
        })

    summary = {
        "fetchedAt": fetched_at_utc,
        "pageTitle": page.get("title"),
        "startBlocks": [
            {"tab": s["context"]["tab"], "bestof": s["context"]["bestof"], "charOffset": s["start"]}
            for s in starts
        ],
        "seriesTotal": len(series),
        "completed": completed,
        "scheduledCandidate": candidates,
        "rows": rows,
    }
    (OUT_DIR / "road-to-msi-result.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(f"Start blocks: {len(starts)} -> {[(s['context']['tab'], s['context']['bestof']) for s in starts]}")
    print(f"series total: {len(series)} completed={completed} scheduled_candidate={candidates}")
    for row in rows:
        if row["classification"] == "SCHEDULED_CANDIDATE":
            print(f"  CANDIDATE {row['contextTab']} {row['team1']} vs {row['team2']} {row['date']} {row['time']}"
                  f" tz={row['timezone']} dst={row['dst']} score={row['team1score']}/{row['team2score']}"
                  f" winner={row['winner']!r} games={row['gameCount']} rpgids={row['gameRpgids']}")
            print(f"    allArgs={json.dumps(row['allArgs'], ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
