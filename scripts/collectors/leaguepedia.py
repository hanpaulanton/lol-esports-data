"""Leaguepedia collector.

Fetches Leaguepedia (Fandom) data and stores the raw API/page responses
unmodified under raw/leaguepedia/. This collector does NOT normalize data.

Sources fetched (PHASE 16):
1. action=cargotables          -> raw/leaguepedia/cargotables.json
2. action=query (revisions)    -> raw/leaguepedia/page_*.json (+ .wikitext extract)
   Used as a fallback source of observed match data while
   action=cargoquery is rate limited (see docs/leaguepedia-schema.md).

Usage:
    python scripts/collectors/leaguepedia.py cargotables --out-dir raw/leaguepedia
    python scripts/collectors/leaguepedia.py page --title "Data:LCK/2026 Season/Rounds 3-4" --out-dir raw/leaguepedia

Exits non-zero on unrecoverable failures (rate limit exhausted, HTTP errors,
query errors, malformed JSON). Raw files already on disk are never deleted.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from lib.fetch import (  # noqa: E402
    FetchError,
    HttpError,
    MalformedJsonError,
    QueryError,
    RateLimitedError,
    fetch_api_json,
    fetch_raw,
)

API_BASE = "https://lol.fandom.com/api.php"


def collect_cargotables(out_dir: pathlib.Path) -> int:
    result = fetch_api_json(API_BASE, {"action": "cargotables", "format": "json"})
    out_path = out_dir / "cargotables.json"
    out_path.write_text(result.body_text, encoding="utf-8") 
    print(f"saved {out_path}")
    return 0


def collect_page_wikitext(title: str, out_dir: pathlib.Path) -> int:
    """Fetch the wikitext of a page and store the raw JSON response plus a
    convenience .wikitext extract. The raw JSON file is the canonical artifact;
    the .wikitext file is a verbatim copy of the revision content field."""
    params = {
        "action": "query",
        "titles": title,
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "format": "json",
        "formatversion": "2",
    }
    result = fetch_api_json(API_BASE, params)
    safe_name = title.replace("/", "_").replace(":", "_")
    json_path = out_dir / f"page_{safe_name}_wikitext.json"
    json_path.write_text(result.body_text, encoding="utf-8") 

    payload = result.body_json 
    pages = payload["query"]["pages"] 
    if not pages or "revisions" not in pages[0]:
        print(f"page has no revisions: {title}", file=sys.stderr)
        return 1
    wikitext = pages[0]["revisions"][0]["slots"]["main"]["content"]
    wikitext_path = out_dir / f"page_{safe_name}.wikitext"
    wikitext_path.write_text(wikitext, encoding="utf-8")
    print(f"saved {json_path}")
    print(f"saved {wikitext_path}")
    return 0


def collect_cargoquery(table: str, out_dir: pathlib.Path, limit: int) -> int:
    """Attempt a cargoquery fetch (may be rate limited; kept separate from the
    wikitext path so one failing action never blocks the other)."""
    params = {
        "action": "cargoquery",
        "tables": table,
        "format": "json",
        "limit": str(limit),
    }
    result = fetch_api_json(API_BASE, params)
    out_path = out_dir / f"{table.lower()}_sample.json"
    out_path.write_text(result.body_text, encoding="utf-8") 
    print(f"saved {out_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Leaguepedia raw data collector")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_tables = subparsers.add_parser("cargotables", help="fetch the Cargo table list")
    p_tables.add_argument("--out-dir", default="raw/leaguepedia")

    p_page = subparsers.add_parser("page", help="fetch a page wikitext (raw JSON + extract)")
    p_page.add_argument("--title", required=True)
    p_page.add_argument("--out-dir", default="raw/leaguepedia")

    p_query = subparsers.add_parser(
        "cargoquery",
        help="attempt a cargoquery fetch (rate limited in practice; manual use)",
    )
    p_query.add_argument("--table", required=True)
    p_query.add_argument("--limit", type=int, default=3)
    p_query.add_argument("--out-dir", default="raw/leaguepedia")

    args = parser.parse_args(argv)
    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        if args.command == "cargotables":
            return collect_cargotables(out_dir)
        if args.command == "page":
            return collect_page_wikitext(args.title, out_dir)
        if args.command == "cargoquery":
            return collect_cargoquery(args.table, out_dir, args.limit)
    except RateLimitedError as exc:
        print(f"RATE_LIMITED: {exc}", file=sys.stderr)
        print(
            "cargoquery remains rate limited; data pages were NOT overwritten. "
            "Wait longer and retry, or keep using the page-wikitext path.",
            file=sys.stderr,
        )
        return 2
    except (HttpError, QueryError, MalformedJsonError, FetchError) as exc:
        print(f"FETCH-FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
