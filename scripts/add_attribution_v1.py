"""PHASE LIC: add license + attribution metadata to the production envelope.

Script-only change to data/matches.json (hand edits are forbidden):
- adds the top-level fields `license` and `attribution` (after generatedAt)
- dataVersion -> 2026.10.14.01, generatedAt -> run time (UTC)
- leagues / teams / matches / schemaVersion MUST be identical afterwards; the
  script asserts this and writes nothing if any assertion fails.
- serialization is identical to the existing file (indent=2, ensure_ascii=False,
  trailing newline, original key order); the script asserts that the existing
  file round-trips through this serializer before it changes anything.
"""

from __future__ import annotations

import copy
import datetime
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "data" / "matches.json"

NEW_VERSION = "2026.10.14.01"
LICENSE = "CC-BY-SA-3.0"
ATTRIBUTION = {
    "source": "Leaguepedia",
    "url": "https://lol.fandom.com",
    "license": "CC BY-SA 3.0",
    "licenseUrl": "https://creativecommons.org/licenses/by-sa/3.0/",
    "notice": "Derived from Leaguepedia; normalized by an unofficial fan project. Not affiliated with Riot Games or Fandom.",
}
VERSION_RE = re.compile(r"^(\d{4})\.(\d{2})\.(\d{2})\.(\d{2})$")


def _version(value: str) -> tuple[int, ...]:
    match = VERSION_RE.match(value or "")
    assert match, f"malformed dataVersion {value!r}"
    return tuple(int(g) for g in match.groups())


def _dump(doc: dict) -> str:
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def main() -> None:
    raw_text = CANONICAL.read_text(encoding="utf-8")  # universal newlines
    before = json.loads(raw_text)

    assert "license" not in before and "attribution" not in before, "already applied"
    assert list(before.keys()) == ["schemaVersion", "dataVersion", "generatedAt", "leagues", "teams", "matches"], list(before.keys())
    assert _dump(before) == raw_text, "existing file does not round-trip through the serializer; aborting"
    assert _version(before["dataVersion"]) < _version(NEW_VERSION), "dataVersion must increase"

    generated_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    after: dict = {}
    for key, value in before.items():
        if key == "dataVersion":
            value = NEW_VERSION
        elif key == "generatedAt":
            value = generated_at
        after[key] = copy.deepcopy(value)
        if key == "generatedAt":
            after["license"] = LICENSE
            after["attribution"] = copy.deepcopy(ATTRIBUTION)

    # ---- immutability assertions (nothing is written if any fails) ----
    for key in ("schemaVersion", "leagues", "teams", "matches"):
        assert after[key] == before[key], f"{key} changed"
    assert after["matches"] is not before["matches"]
    assert [m["id"] for m in after["matches"]] == [m["id"] for m in before["matches"]], "match ids/order changed"
    assert [t["id"] for t in after["teams"]] == [t["id"] for t in before["teams"]], "team ids/order changed"
    assert set(after) - set(before) == {"license", "attribution"}
    assert {k for k in before if before[k] != after.get(k)} == {"dataVersion", "generatedAt"}

    CANONICAL.write_text(_dump(after), encoding="utf-8")
    print(f"dataVersion: {before['dataVersion']} -> {NEW_VERSION}")
    print(f"generatedAt: {before['generatedAt']} -> {generated_at}")
    print(f"added: license={LICENSE!r}, attribution ({len(ATTRIBUTION)} fields)")


if __name__ == "__main__":
    main()
