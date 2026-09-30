# External Source Policy Event Model (fail-closed)

External source policies (API terms, license, robots, rate limits) may change at
any time. This pipeline never auto-accepts changed terms: **it fails closed and
requires human review.**

## Where policy state lives

```
config/policies/<source>.json      # per-source policy metadata (human-edited)
policy_snapshots/<source>/<date>.json
                                   # machine-written: checkedAt / termsUrl /
                                   # contentHash / observedStatus
scripts/policy/check_policies.py   # fetch + hash + compare (exit 1 on change)
```

## Events and default actions

| Event | Detection (planned) | Default action |
|---|---|---|
| `TERMS_CHANGED` | policy checker hash differs from previous snapshot | **STOP collection** + CI failure + human review. Canonical data is kept as-is. |
| `ROBOTS_CHANGED` | robots.txt hash differs (checker extension, PHASE 19) | **STOP collection** + human review |
| `API_SCHEMA_CHANGED` | collector parse/validation fails on known fields | collector test fails + **STOP** that source's collector (other sources unaffected) |
| `RATE_LIMIT_CHANGED` | new/changed rate-limit error patterns | collection policy (frequency/backoff) re-evaluation — no data deletion |
| `SOURCE_UNAVAILABLE` | HTTP 5xx/403/network failure at collect time | retry with backoff → if still failing, skip this run; **stale canonical data stays published** |

Hard rules:

1. A policy change never deletes existing canonical JSON.
2. A policy change never auto-adopts a new source.
3. A policy change never changes the Android app's data URL.
4. Each source's collector is independent (`scripts/collectors/<source>.py`);
   a policy event for one source must not stop the others.
5. API schema changes and terms changes are tracked as separate events.

## Current snapshot status (2026-09-29)

- `leaguepedia`: **SOURCE_UNAVAILABLE** for terms (Fandom ToS returns 403 to
  HTTP clients) — collection stays low-frequency with backoff; a human must
  review the Fandom Terms of Use in a real browser and re-run the checker to
  record a real hash baseline.
- `oracle_elixir`: **BASELINE** recorded (hash of the served HTML shell; the
  visible terms wording was verified in a browser and is quoted in
  `config/policies/oracle_elixir.json`). Note: the page is client-rendered, so
  the shell hash detects served-byte changes only; periodic manual browser
  review is part of the operating procedure.
- `liquipedia`: `collectionAllowed: false` (terms page 403 to HTTP clients;
  community-documented strict rate limits unverified). Backup-only source.
