# lol-esports-data

Data pipeline repository for a personal, unofficial, fan-made League of Legends
esports schedule Android app. **This repository is separate from the Android app
repository.**

- Unofficial fan project. Not affiliated with, endorsed by, or connected to
  Riot Games. League of Legends and Riot Games are trademarks of Riot Games, Inc.
- Non-commercial, no ads, no login, no payments, no analytics.
- Target operating cost: **0 KRW / 0 USD** (free public sources + GitHub
  Actions/Pages free tiers; no servers, no databases, no API keys).

## Data source & license

- **Data**: schedule and result data is derived from
  [Leaguepedia](https://lol.fandom.com), (c) Leaguepedia contributors, licensed
  under [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/).
  Changes: extracted and normalized into JSON; times converted to UTC. The data
  files in this repository are therefore also licensed under CC BY-SA 3.0 - see
  `LICENSE-DATA`.
- **Code**: MIT License - see `LICENSE`.
- This repository does **not** redistribute third-party page text (wiki text,
  terms-of-service copies, etc.). Such raw material was removed from the public
  repository and its history (PHASE LIC) and is kept locally only; `raw/`,
  `phase*-test/` and `_local-evidence/` are git-ignored. Tests that need those
  files are skipped when they are absent.
- Unofficial fan project; not affiliated with Riot Games or Fandom.

## Current status

- **v1 data is in production**: `data/matches.json` (canonical, `schemaVersion 1`)
  is published through GitHub Pages and consumed by the Android app. See
  `CLAUDE.md` and the root `PROJECT-HANDOFF.md` for the audited promotion history.
- **v2 redesign is planned** (automatic refresh from the Leaguepedia Cargo API
  with automated validation gates): see `docs/pipeline-v2-design.md`.
- **Oracle's Elixir** is a secondary verification candidate (not implemented);
  **Liquipedia** is backup-only (`collectionAllowed: false`).

## Collection principles

- Low-frequency collection only, with exponential backoff (1s, 2s, 4s, 8s, cap
  30s) and a hard attempt limit; `ratelimited` JSON errors are retried, other
  errors fail fast.
- **Raw data and normalized data are strictly separated.** Raw responses are
  stored locally only (not in this repository); `data/` holds the normalized
  canonical output.
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
data/              normalized canonical output (matches.json)
docs/              observed schema, policy event model, design documents
policy_snapshots/  per-source terms snapshots (hash + status)
raw/               (local only, git-ignored) unmodified collected responses
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
