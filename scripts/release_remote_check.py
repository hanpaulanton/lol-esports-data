"""PHASE 18-17: MANUAL release gate — remote GitHub Pages smoke check.

This script is intentionally NOT named test_*.py so unittest discovery never
runs it: the normal unit-test suite must stay fully offline. Run it by hand
when verifying a release (see docs/production-contract-gate.md).

Usage (from the repository root):
    python scripts/release_remote_check.py

What it does:
1. Fetches the production canonical JSON from GitHub Pages.
2. Verifies the HTTP status and parses the JSON.
3. Compares the remote document to the local data/matches.json (semantic
   parsed-JSON equality — no byte/newline comparison).
4. Runs the exact same offline production contract gate that the unit tests
   use (tests/test_production_contract.collect_problems).
5. Exits non-zero on any failure.

Standard library only (plus the repo's own lib/fetch USER-Agent helper).
"""

from __future__ import annotations

import json
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from lib.fetch import USER_AGENT  # noqa: E402
from test_production_contract import BASELINE, collect_problems, parse_version  # noqa: E402

PRODUCTION_URL = "https://hanpaulanton.github.io/lol-esports-data/data/matches.json"
LOCAL = ROOT / "data" / "matches.json"


def fetch_remote() -> dict:
    request = urllib.request.Request(PRODUCTION_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        status = response.status
        if status != 200:
            raise SystemExit(f"FAIL: production URL returned HTTP {status}")
        content_type = response.headers.get("Content-Type", "")
        body = response.read().decode("utf-8")
    print(f"HTTP {status} | content-type: {content_type}")
    if "json" not in content_type.lower():
        print(f"WARN: unexpected content-type {content_type!r}")
    return json.loads(body)


def main() -> None:
    local = json.loads(LOCAL.read_text(encoding="utf-8"))

    remote = fetch_remote()
    print(f"remote dataVersion: {remote.get('dataVersion')} | teams: {len(remote.get('teams', []))} | matches: {len(remote.get('matches', []))}")

    if remote != local:
        raise SystemExit("FAIL: remote canonical JSON differs from local data/matches.json")
    print("remote == local (semantic parsed-JSON equality): OK")

    problems = collect_problems(remote)
    if problems:
        print(f"FAIL: production contract gate reported {len(problems)} problem(s):")
        for problem in problems:
            print(f"  - {problem}")
        raise SystemExit(1)
    print("production contract gate on remote document: PASS")

    version = parse_version(remote.get("dataVersion", ""))
    baseline = parse_version(BASELINE["dataVersion"])
    if version is None or baseline is None or version < baseline:
        raise SystemExit(
            f"FAIL: remote dataVersion {remote.get('dataVersion')!r} is malformed or "
            f"below the approved baseline {BASELINE['dataVersion']!r}"
        )
    print(f"dataVersion {remote.get('dataVersion')} >= baseline {BASELINE['dataVersion']}: OK")
    print("RELEASE REMOTE CHECK: PASS")


if __name__ == "__main__":
    main()
