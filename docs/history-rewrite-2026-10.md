# History rewrite 2026-10 (PHASE LIC)

On 2026-10-14/15 the git history of this repository was rewritten to remove
third-party material that must not be redistributed from a public repository.
The earlier SHAs referenced in documents and commit messages (e.g. `PHASE 18-x`
reports, `PROJECT-HANDOFF.md`) therefore no longer exist; use the table below.

## What was removed (from the working tree and from every past commit)

| Path | Reason |
|---|---|
| `raw/` | unmodified Leaguepedia API/page responses (wiki text) |
| `phase18-3a-test/`, `phase18-3c-test/` | investigation dumps derived from raw wiki pages |
| `phase18nw-test/` | rendered copies of namu.wiki pages and its terms/policy pages (CC BY-NC-SA 2.0 KR, a different license) |
| `tests/scheduled_schema_result.json`, `tests/scheduled_fetch_result.json` | contain verbatim wikitext game blocks |
| `docs/scheduled-match-schema.md` (old revisions) | quoted verbatim wikitext blocks; the current version was re-added in the last commit with structure descriptions instead |

Kept: our own code, docs, normalized data, `policy_snapshots/` (hashes and
notes only), and `tests/fixtures/page_wikitext_200.json` (a 687-byte fixture
needed by the collector tests).

The removed raw material exists only locally (`_local-evidence/`, outside git)
and is git-ignored (`raw/`, `phase*-test/`, `_local-evidence/`, `p0-spike/`).
77 tests that need those fixtures are skipped when the files are absent
(`unittest.skipUnless`, logic unchanged). `tests/test_production_contract.py`
runs without them.

## SHA mapping (old -> new)

Only the 10 commits that existed before PHASE LIC are mapped. The PHASE LIC
commits were never published under their old SHAs.

| old SHA | new SHA | subject |
|---|---|---|
| 7a81460 | 0221536 | PHASE 18-24: convert Worlds Play-In scheduled times to verified UTC |
| 5933272 | 8818a0e | PHASE 18-22: transition 10 EMEA TBD scheduled matches to completed in place |
| 1fd2748 | f4c407c | PHASE 18-21: transition 14 EMEA scheduled matches to completed in place |
| 19205da | cf6bc64 | PHASE 18-20: ingest verified EMEA Masters completed matches |
| f51c0c1 | b0f77bb | PHASE 18-17: production canonical data contract regression gate |
| b67121e | 706b62f | PHASE 18-15: promote verified EMEA identities and convert EMEA scheduled times to UTC |
| b2416bb | 633af5c | Bump dataVersion to 2026.10.01.01 per promotion versioning policy (PHASE 18-12) |
| e1dc601 | 4a63ec5 | Promote verified LCK team identities to canonical teams |
| 6e89f2f | 73d4503 | Disable Jekyll for static data Pages |
| d442fea | 2a7e9b8 | Phase 18-9 validated canonical data baseline |

Commit count and subject order of the pre-existing 10 commits are unchanged.

## Verification performed

- `git log --all --name-only` and a walk over every commit tree contain none of
  the removed paths.
- `data/matches.json` at HEAD is byte-identical to the pre-rewrite file after
  PHASE LIC step 2 (license/attribution fields only).
- Full test suite at the rewritten HEAD: 170 run, 77 skipped, 0 failures.
- A full mirror backup taken before the rewrite is kept locally (not in git).

## Note on cached views

GitHub may keep serving old commits by SHA for a while. GitHub Support can
purge cached views via the "Removing sensitive data from a repository"
procedure.
