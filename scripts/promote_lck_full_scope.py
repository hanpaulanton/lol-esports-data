"""PHASE 18-9 STEP 7: full-scope LCK completed normalization.

Re-normalizes ALL 40 series of the Rounds 3-4 raw fixture (Weeks 10-13)
using the existing normalize_sample.normalization logic, without the
sample's first-tab-only scoping and without touching matches.sample.json.

Output (in-memory list + printed summary) feeds the PHASE 18-9 canonical
envelope builder. Excluded series (unmapped team codes etc.) are reported
verbatim — never silently dropped.
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import normalize_sample as ns  # noqa: E402


def main() -> tuple[list[dict], list[dict]]:
    wikitext = ns.RAW_PAGE.read_text(encoding="utf-8")
    series, starts = ns.collect_series(wikitext)
    # Full scope: every series in the fixture (no first-tab filter).
    normalized, excluded = ns.normalize(series)
    print(f"series_total={len(series)} normalized={len(normalized)} excluded={len(excluded)}")
    for item in excluded:
        problems = "; ".join(item["problems"])
        print(f"  EXCLUDED {item['id']}: {problems}")
    return normalized, excluded


if __name__ == "__main__":
    normalized, excluded = main()
    out = ROOT / "phase18-3a-test" / "lck_full_scope_completed.json"
    out.write_text(json.dumps(normalized, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"written: {out.relative_to(ROOT)} ({len(normalized)} records)")
