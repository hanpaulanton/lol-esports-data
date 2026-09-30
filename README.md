# lol-esports-data

Data pipeline repository for a personal, unofficial, fan-made League of Legends
esports schedule Android app. **This repository is separate from the Android app
repository.**

- Unofficial fan project. Not affiliated with, endorsed by, or connected to
  Riot Games. League of Legends and Riot Games are trademarks of Riot Games, Inc.
- Non-commercial, no ads, no login, no payments, no analytics.
- Target operating cost: **0 KRW / 0 USD** (free public sources + GitHub
  Actions/Pages free tiers; no servers, no databases, no API keys).

## Current status (PHASE 16)

- **Leaguepedia** (lol.fandom.com) is being investigated as the **primary**
  source. Raw samples were collected on 2026-09-29 (see `raw/leaguepedia/` and
  `docs/leaguepedia-schema.md`). Observed: `api.php?action=cargotables` and
  `api.php?action=query` work; `action=cargoquery` is persistently rate limited
  from this environment, so a page-wikitext fallback path is also implemented.
- **Oracle's Elixir** is being investigated as the **secondary verification**
  source (completed-match results). Its downloads page terms were verified in a
  browser on 2026-09-29: data is provided free of charge, files are updated
  **once per day**, game statistics are the property of Riot Games and usage
  must follow Riot's terms and policies, and some content is provided courtesy
  of Leaguepedia under CC-BY-SA 3.0. No explicit redistribution license for the
  CSV files was stated on the page (recorded as unconfirmed).
- **Liquipedia** is backup-only; its API terms page returns 403 to plain HTTP
  clients, so automation against it is not attempted (`collectionAllowed: false`).

## Collection principles

- Low-frequency collection only, with exponential backoff (1s, 2s, 4s, 8s, cap
  30s) and a hard attempt limit; `ratelimited` JSON errors are retried, other
  errors fail fast. Oracle's Elixir files must not be downloaded more than once
  per day (per the page's own wording).
- **Raw data and normalized data are strictly separated.** `raw/` stores
  unmodified API/page responses; `data/` will hold normalized canonical output.
- **A production canonical `matches.json` has NOT been produced yet** (that is
  the normalizer phase). The Android app remains on its bundled sample data.
- **The Android app has NOT been connected to this repository's output.** The
  app's `DEFAULT_DATA_URL` is unchanged.
- No CAPTCHA/Cloudflare circumvention, no block evasion, no API keys.

## Policy-change safety (fail closed)

External source policy changes are treated as human-review events. The
pipeline fails closed rather than automatically accepting changed terms:
`TERMS_CHANGED` / `ROBOTS_CHANGED` stop collection and keep existing canonical
data; nothing is ever auto-approved or deleted. See
`docs/policy-event-model.md`, `config/policies/`, and `policy_snapshots/`.

## Layout

```
config/            source registry + per-source policy metadata
data/              normalized canonical output (empty; future phase)
docs/              observed schema + policy event model
policy_snapshots/  per-source terms snapshots (hash + status)
raw/               unmodified collected responses (leaguepedia/)
schema/            canonical schema definitions (future phase)
scripts/
  collectors/      one collector per source (leaguepedia.py implemented)
  policy/          check_policies.py (fail-closed change detector)
  lib/             shared fetch/backoff helpers (stdlib only)
tests/             offline unit tests + saved fixtures
```

## Running (Python 3.10+, standard library only)

```
python scripts/policy/check_policies.py          # record/compare policy snapshots
python scripts/collectors/leaguepedia.py cargotables --out-dir raw/leaguepedia
python scripts/collectors/leaguepedia.py page --title "Data:LCK/2026 Season/Rounds 3-4" --out-dir raw/leaguepedia
python -m unittest discover -s tests             # offline unit tests
```

`requirements.txt` intentionally pins nothing: the scripts use only the Python
standard library. Real Leaguepedia API access is a manual integration activity;
unit tests run fully offline against local fixtures/servers.

## User-Agent

Collectors identify as
`LoLEsportsFanDataCollector/0.1 (unofficial fan project; personal non-commercial)`.
If a source requires contact information, this README is the designated place
to record it before enabling that source.
