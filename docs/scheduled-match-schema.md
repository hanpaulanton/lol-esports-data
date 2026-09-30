# Scheduled Match Schema Investigation

> PHASE 18-3-B UPDATE (2026-09-30): 泥?吏꾩쭨 scheduled ?덉떆媛 ?뺣낫?섏뼱 ?섎떒
> "PHASE 18-3-B ??First Genuine Scheduled Example (Worlds 2026 Play-In)"
> ?뱀뀡??異붽??섏뿀?듬땲?? ?곷떒??湲곗〈 ?댁슜? PHASE 18-2 ?쒖젏(offline-only,
> scheduled ?덉떆 0嫄???愿痢?湲곕줉?쇰줈 蹂댁〈?⑸땲??

- 議곗궗 ?쇱떆: 2026-09-30
- 踰붿쐞: **raw-only** ???ㅽ듃?뚰겕 ?붿껌 0嫄? production canonical data 蹂寃??놁쓬, Android 蹂寃??놁쓬
- ?꾧뎄: `tests/scheduled_schema_investigation.py`, `tests/detail_checks.py`, `tests/hle_dplus_gameid_matching.py`
- 湲곌퀎 ?먮룆 寃곌낵: `tests/scheduled_schema_result.json`

## Scope
- ??λ맂 raw fixture留?遺꾩꽍 (?좉퇋 ?섏쭛 ?놁쓬)
- production canonical data / Android / GitHub ?ㅼ젙 臾대?寃?
## Source Files Examined

| ?뚯씪 | 議댁옱 | ?⑸룄 | 愿痢?|
|---|---|---|---|
| `raw/leaguepedia/page_data_lck_rounds34.wikitext` (54,964B) | O | **MatchSchedule ?쒕━利?寃뚯엫 ?꾩껜 遺꾩꽍 ???* | ?쒕━利?40, Start 4, Game 99 |
| `raw/leaguepedia/page_data_lck_rounds34_wikitext.json` (56,536B) | O | ?숈씪 ?묐떟??raw JSON 蹂댁〈 | 蹂몃Ц ?숈씪 |
| `raw/leaguepedia/page_lck_rounds34.wikitext` (14,185B) | O | ?좊꼫癒쇳듃 ?섏씠吏 (Infobox/濡쒖뒪?? | **MatchSchedule 0嫄?* [?뺤씤] |
| `raw/leaguepedia/page_lck_rounds34_wikitext.json` | O | ?숈씪 ?묐떟 蹂댁〈 | ??|
| `raw/leaguepedia/page_lck_scoreboards.wikitext` (102,584B) | O | 寃뚯엫 ?⑥쐞 ?ㅼ퐫?대낫??| MatchSchedule 0嫄? `Scoreboard/Season 16` 14嫄?寃뚯엫 ?⑥쐞) |
| `raw/leaguepedia/page_lck_scoreboards_wikitext.json` | O | ?숈씪 ?묐떟 蹂댁〈 | ??|
| `raw/leaguepedia/cargotables.json`, `fetched_at.txt` | O | 李멸퀬 | ??|

- 蹂댁“ ?뺤씤: `config/team_mappings.json` (PHASE 18-1 寃利?寃곌낵 諛섏쁺), `tests/scheduled_schema_result.json`

## Observed MatchSchedule Structures

### Completed
- **40媛??쒕━利??꾨?媛 COMPLETED 援ъ“濡?愿痢?* [?뺤씤]
- 怨듯넻 援ъ“: `winner`(1/2) + `team1score`/`team2score`(?レ옄) + `game1`/`game2`(+ 3?명듃 ??`game3`) 議댁옱
- 寃뚯엫 ?뱀옄 吏묎퀎瑜?**?ъ씠???ㅼ솑??諛섏쁺**???쒕━利??ㅼ퐫?댁? ?議고븯硫?**40/40 ?꾩쟾 ?쇱튂** [?뺤씤]
- ?쒕━利덈퀎 寃뚯엫 ?? 2~3媛? ?ㅼ퐫?????뚮젅?대맂 寃뚯엫 ??: 2~3 ??BO3 踰붿쐞 ???덉쇅 ?놁쓬 [?뺤씤]

### Scheduled Candidate
- **0媛?* ?????fixture???덉젙 寃쎄린濡?遺꾨쪟?????덈뒗 MatchSchedule ?쒗뵆由우씠 議댁옱?섏? ?딆쓬 [?뺤씤]
- 援ъ“??洹쇨굅媛 ??留뚰븳 ?붿냼(?덉젙 ?꾩슜 ?몄옄, 鍮?game 釉붾줉, status ?꾨뱶 ????40???꾩껜?먯꽌 誘멸?痢?[?뺤씤]
- ?곕씪???덉젙 寃쎄린???ㅼ젣 template 援ъ“????fixture留뚯쑝濡쒕뒗 **?뺤젙 遺덇?**

### Unknown
- 遺꾨쪟 UNKNOWN: **0媛?*

## Field-Level Findings

`{{MatchSchedule}}` ?쒕━利?40???꾩껜?먯꽌 愿痢〓맂 ?꾩껜 ?몄옄 ??鍮덈룄:
`team1=40, team2=40, team1score=40, team2score=40, winner=40, date=40, time=40, timezone=40, dst=40,
initialorder=40, pbp=40, color=40, vodinterview=40, with=40, mvp=40, vodhl=40, stream=40, reddit=40,
game1=40, game2=40, game3=19`

| Field | Completed (40??愿痢? | Scheduled Candidate (0?? | Evidence | Status |
|------|-----------|---------------------|----------|--------|
| team1 | ??긽 議댁옱 (異뺤빟 肄붾뱶, ??`HLE`) | **UNKNOWN** ???덉떆 ?놁쓬 | 40/40 ?됱뿉??愿痢? 肄붾뱶 10醫?| OBSERVED |
| team2 | ??긽 議댁옱 | **UNKNOWN** | 40/40 | OBSERVED |
| team1score | ??긽 議댁옱, ?뺤닔(0~2) | **UNKNOWN** (?뺥깭 誘명솗?? 鍮?媛?0/誘몄〈??紐⑤몢 媛?μ꽦) | 40/40 ?뺤닔 | OBSERVED (?꾨즺留? |
| team2score | ??긽 議댁옱, ?뺤닔(0~2) | **UNKNOWN** | 40/40 | OBSERVED (?꾨즺留? |
| winner | ??긽 議댁옱, 1 ?먮뒗 2 | **UNKNOWN** | 40/40 | OBSERVED (?꾨즺留? |
| date | ??긽 議댁옱, `YYYY-MM-DD` (2026-07-29~08-23) | **UNKNOWN** | 40/40 | OBSERVED |
| time | ??긽 議댁옱, `HH:MM` (17:00/19:00 ?? | **UNKNOWN** | 40/40 | OBSERVED |
| timezone | ??긽 議댁옱, `KST` ?⑥씪 | **UNKNOWN** | 40/40 | OBSERVED |
| dst | ??긽 議댁옱, `yes` ?⑥씪 (KST? 紐⑥닚 ??PHASE 17 寃쎄퀬) | **UNKNOWN** | 40/40 | OBSERVED |
| bestof (?쒕━利덈퀎) | **0?됱뿉??愿痢?* ???몄옄 ?먯껜 ?놁쓬 | **UNKNOWN** | 40???꾩껜 寃??| NOT_OBSERVED |
| bestof (Start ???⑥쐞) | 4媛?Start 紐⑤몢 `bestof=3` | ?숈씪 援ъ“濡??덉젙???곸슜??寃껋쑝濡?**異붿젙 遺덇?** | 4/4 | OBSERVED (媛? / INFERRED (踰붿쐞) |
| MatchSchedule/Game | 40???꾨? 議댁옱: game1/game2 40?됱뵫, game3 19??| **UNKNOWN** ???덉젙 ?됱뿉??Game 釉붾줉??議댁옱 ?뺥깭 誘멸?痢?| 99媛?Game ?쒗뵆由?| OBSERVED (?꾨즺留? |
| riot_platform_game_id | 99媛?寃뚯엫 以?98媛?議댁옱, 1媛?鍮?媛?(`GEN vs DPLUS` 08-01 game1 ??`ff`/`vodpb` ???ㅻⅨ ?몄옄??議댁옱) | **UNKNOWN** ???덉젙 寃쎄린?먯꽌 ?ъ쟾 遺???щ? 誘멸?痢?| 98/99 | OBSERVED |
| 湲고? (pbp/color/mvp/with/stream/reddit/vod*) | 40?됰쭏??議댁옱 (媛??ㅼ뼇) | **UNKNOWN** | ??| OBSERVED (?꾨즺留? |

`{{MatchSchedule/Game}}` ?꾨즺 寃뚯엫???몄옄 ??鍮덈룄(99寃뚯엫 ?꾨? ?숈씪 ?명듃):
`blue=99, red=99, winner=99, riot_platform_game_id=98, first_sel=99, ssel=99, pick_sel=99, first_pick=99,
ff=99, vod=99, vodpb=99, vodstart=99, vodpost=99, vodhl=99, vodinterview=99, with=99, mvp=99`

## BestOf Scope

1. **臾몄꽌 ?쒖꽌 援ъ“ [?뺤씤]**: `Start(Week 10)` ???쒕━利?10媛???`Start(Week 11)` ??10媛???`Start(Week 12)` ??10媛???   `Start(Week 13)` ??10媛? 泥??쒕━利덈뒗 泥?Start **?댄썑**???꾩튂, 留덉?留??쒕━利??댄썑 Start ?놁쓬.
2. **?곸슜 踰붿쐞 愿痢?[?뺤씤]**: 媛?Start???뺥솗???먭린 二쇱감??10媛??쒕━利??욎뿉 ?꾩튂(10/10/10/10) ??   "Start遺???ㅼ쓬 Start 吏곸쟾源뚯?"?쇰뒗 援ъ“???⑦꽩怨??쇱튂.
3. **?뺥빀??寃利?[?뺤씤]**: 40???꾨??먯꽌 `team1score+team2score ??3`(Start??bestof) ??紐⑥닚 0嫄?
4. **?쒕━利덈퀎 override**: ?쒕━利??몄옄??bestof 怨꾩뿴 ??**0嫄?* [?뺤씤] ??override 議댁옱 ?щ? NOT_OBSERVED.
5. **?덉쇅(BO1/BO5 ??**: ?ㅼ퐫????2~3留?愿痢? 寃뚯엫 ??2~3留?愿痢????덉쇅 利앷굅 ?놁쓬 [?뺤씤].
6. **誘명솗??*: "Start?믩떎??Start" ?ㅼ퐫?꾧? ?꾪궎 ?붿쭊???ㅼ젣 ?섎?濡좎씤吏??援ъ“ 愿痢≪쓽 **INFERRED**?대ŉ,
   ?덉젙 寃쎄린(?쒖옉 ????Start媛 議댁옱?섎뒗吏????fixture濡??뺤씤 遺덇? ??UNKNOWN.

## Scheduled Detection Rule

```text
NOT YET DETERMINED
```

- ???fixture???덉젙 寃쎄린 ?덉떆媛 ?꾨Т?섎?濡? scheduled ?먯젙 洹쒖튃??source evidence 湲곕컲?쇰줈 ?뺤쓽?????놁쓬.
- "score/winner 遺??= scheduled" 媛숈? 洹쒖튃? 湲덉???吏??짠1).
- ?꾨낫 洹쒖튃(?? date媛 ?섏쭛 ?쒖젏 ?댄썑 + game ?쒗뵆由?遺??? ?꾨? 異붾줎?대?濡?梨꾪깮?섏? ?딆쓬.
- ?뺤젙???꾩슂??寃? ?덉젙 寃쎄린媛 ?ы븿????raw ?섑뵆(?ㅺ??ㅻ뒗 二쇱감??`Data:` ?섏씠吏) ?뺣낫.

## Canonical Mapping Implications

- **?덉쟾?섍쾶 ?뺤젙 媛??(?꾨즺 寃쎄린 ?쒖젙, ?꾨? 愿痢?湲곕컲)**:
  - `status = "completed"`: winner + ??? ?ㅼ퐫?닿? 愿痢〓맂 ?쒕━利?  - `score.team1/team2 = team1score/team2score` (愿痢↔컪, 寃뚯엫 ?뱀옄 吏묎퀎? 40/40 ?뺥빀 [?뺤씤])
  - `scheduledAt`: date+time+timezone ??UTC 蹂??KST 寃利??꾨즺, PHASE 17)
  - `bestOf`: ??而⑦뀓?ㅽ듃 + ?ㅼ퐫???뺥빀??寃利??듦낵 ?쒖뿉留?(PHASE 17 諛⑹떇 ?좎?)
  - `id`: deterministic synthetic (PHASE 17 洹쒖튃)
  - `team1Id/team2Id`: Leaguepedia 肄붾뱶 (PHASE 18-1?먯꽌 10媛??꾨? ?대쫫 留ㅽ븨 ?뺤젙 ??provisional ?앸퀎?먯엫? ?좎?)
- **?뺤젙 遺덇? ??canonical???ｌ? ?딆쓬**:
  - `status = "scheduled"` (?덉젙 row 援ъ“ 誘멸?痢?
  - `score = 0:0` 媛숈? ?덉젙 湲곕낯媛?洹쒖튃 (evidence ?놁쓬)
  - ?덉젙 寃쎄린??`bestOf` (Start 媛??곸슜 洹쇨굅媛 ?덉젙 寃쎄린?먯꽌 誘멸?痢?
  - ?덉젙 寃쎄린??`riot_platform_game_id` ?ъ쟾 議댁옱 ?щ?
- 寃곕줎: **?꾨즺 寃쎄린??canonical ?밴꺽? ?덉쟾, ?덉젙 寃쎄린 ?밴꺽? 利앷굅 ?뺣낫 ?꾧퉴吏 湲덉?.**

## Open Questions

1. ?덉젙 寃쎄린??MatchSchedule row???대뼡 ?뺥깭?멸? (game 釉붾줉 ?좊Т, score/winner ?쒓린)?
2. ?덉젙 寃쎄린??`riot_platform_game_id`媛 ?ъ쟾 遺?щ릺?붽??
3. ?쒕━利덈퀎 BestOf ?덉쇅(??대툕?덉씠而??????쒓린 諛⑹떇?
4. `dst=yes`媛 KST ?됱뿉???섎??섎뒗 諛?(PHASE 17 寃쎄퀬 怨꾩냽)?
5. `GEN vs DPLUS` (08-01) game1??鍮?`riot_platform_game_id` ???곗씠???낅젰 ?꾨씫?몄?, ?뱀닔 ?ъ쑀?몄??
6. Start 釉붾줉 諛뽰쓽 ?쒕━利?臾몄꽌 癒몃━/瑗щ━)媛 議댁옱?????덈뒗吏?
7. Weeks ?몄쓽 ???뚮젅?댁삤???먯꽌 Start 援ъ“媛 ?숈씪?쒖??

---

# PHASE 18-3-B ??First Genuine Scheduled Example (Worlds 2026 Play-In)

Observation date: **2026-09-30 (UTC)**. Evidence source: raw fixture
`raw/leaguepedia/page_Data_2026 Season World Championship_Play-In.wikitext`
(saved unmodified by permitted PHASE 18-3-B request #12; request log in
`raw/leaguepedia/phase18_3b_fetch_metadata.json`). Page title:
`Data:2026 Season World Championship/Play-In` (Data namespace 10008).
Everything below is FACT (directly observed in the saved raw wikitext)
unless explicitly labeled INFERENCE or UNKNOWN. Deterministic tests:
`tests/test_playin_scheduled_schema.py`.

## Observed Structure

The page contains 3 `{{MatchSchedule/Start}}` blocks (`tab=Round 1/2/3`,
`bestof=5`, `shownname=Worlds 2026 Play-In`) and **6 `{{MatchSchedule}}`
rows, ALL genuinely scheduled/unplayed**: every row's `date`
(2026-10-15 / 10-15 / 10-16 / 10-16 / 10-17 / 10-18) is in the future
relative to the 2026-09-30 observation. No row carries a completed score.

Raw template shape of a scheduled row (row 1, structural excerpt):

```
{{MatchSchedule|<!-- comment -->|initialorder=1|team1= |team2= |team1score= |team2score= |winner=
|date=2026-10-15 |time=11:00 |timezone=PST |dst=yes |pbp= |color= |vodinterview= |with= |mvp= |vodhl= |stream=https://www.twitch.tv/riotgames |reddit=
|game1={{MatchSchedule/Game
|blue= |red= |winner= |first_sel= |ssel= |pick_sel= |first_pick= |ff=
|riot_platform_game_id=
|vod= |vodpb= |vodstart= |vodpost= |vodhl= |vodinterview= |with= |mvp=
}}
... (game2..game5 identical) ...
}}
```

## MatchSchedule Field Table (scheduled rows)

Classification per handoff section 9: a key present with a value is
OBSERVED; a key present but empty is OBSERVED_ABSENT. No general claim
about Leaguepedia is drawn from this single page.

| Field | Scheduled-row observation (6/6 rows) |
|---|---|
| `team1` | OBSERVED_ABSENT (key present, value empty) |
| `team2` | OBSERVED_ABSENT |
| `team1score` | OBSERVED_ABSENT |
| `team2score` | OBSERVED_ABSENT |
| `winner` | OBSERVED_ABSENT |
| `date` | OBSERVED with value, `YYYY-MM-DD` (2026-10-15..2026-10-18) |
| `time` | OBSERVED with value, `HH:MM` (11:00 or 16:00) |
| `timezone` | OBSERVED with value, `PST` in all 6 rows |
| `dst` | OBSERVED with value, `yes` in all 6 rows |
| `initialorder` | OBSERVED with value (1/2/3) |
| `stream` | OBSERVED with value, `https://www.twitch.tv/riotgames` |
| `pbp`, `color`, `vodinterview`, `with`, `mvp`, `vodhl`, `reddit` | OBSERVED_ABSENT |
| `bestof` (per-series arg) | OBSERVED_ABSENT as a key ??bestof exists on Start only |
| status-like field | OBSERVED_ABSENT ??no status/postponed/cancelled key in any row |

INFERENCE: a scheduled series uses the SAME template and key set as a
completed series, with all result-bearing values empty; only
date/time/timezone/dst/initialorder/stream carry values.
UNKNOWN: whether team1/team2 are ever pre-filled before a match (this page
pre-fills nothing because Play-In participants were undetermined at
observation time); whether partially filled rows exist in other stages.

## MatchSchedule/Game Field Table (scheduled rows)

Handoff section 14 outcome: **A and B combined** ??`{{MatchSchedule/Game}}`
blocks DO exist before the match (5 per row, `game1`..`game5`, matching the
Start's `bestof=5`; 30 game templates over 6 rows), yet all their values are
empty, so no rpgid is preassigned here (B for rpgid, 0/30).

| Field | Observation (30/30 games) |
|---|---|
| blue, red, winner, first_sel, ssel, pick_sel, first_pick, ff, vod, vodpb, vodstart, vodpost, vodhl, vodinterview, with, mvp | OBSERVED_ABSENT (empty) |
| `riot_platform_game_id` | OBSERVED_ABSENT (empty) ??NOT preassigned on this page |
| game arg key set | identical 17-key set as completed games (same as PHASE 18-2) |

UNKNOWN: whether rpgid is preassigned on pages whose matchup is already
determined (this page cannot answer it ??team slots are empty).

## Best-of / Start Context

OBSERVED: each scheduled row sits inside `{{MatchSchedule/Start|tab=Round N
|bestof=5|shownname=Worlds 2026 Play-In}}` ... `{{MatchSchedule/End}}`, and
each row's empty `game1..game5` count exactly equals the Start's `bestof=5`.
Consistent with the PHASE 18-2 "Start ??next Start" scope observation.
UNKNOWN: whether the game-block count always equals bestof for scheduled
rows generally (single-page evidence only).

## DST

OBSERVED: `dst=yes` on all 6 scheduled rows, `timezone=PST`,
dates 2026-10-15..18. Known PST/PDT offsets are general knowledge, NOT
source evidence. Interpretation of `dst=yes` here is **UNKNOWN** (same
anomaly as the KST `dst=yes` completed rows reported in PHASE 17). No UTC
conversion for scheduled rows is derived from this page.

## Postponed / Cancelled

Not observed on this page; no status-like key exists. Postponed/cancelled
schema = **UNKNOWN**.

## Scheduled Detection Implications (for a later phase)

FACT-level signals available from this page: `winner` empty, both score
fields empty, `date` present. Per handoff section 10, "winner empty" alone
must NOT classify a row as scheduled; date support is required, and this
fixture cannot establish whether Leaguepedia ever leaves `winner` empty on
a completed row (no such row observed anywhere yet).
No production normalization or promotion is proposed in this phase.

## Open Questions (added by PHASE 18-3-B)

8. Are team1/team2 ever pre-filled on a scheduled row (once matchups are
   known, e.g. Main Event bracket) ??and in which representation (code vs
   full name)?
9. Is `riot_platform_game_id` preassigned on scheduled rows with known teams?
10. Does `dst=yes` + `timezone=PST` on 2026-10 dates mean the wiki stores
    local wall time plus a separate DST flag, or something else?
11. Do postponed/cancelled rows use empty values like scheduled rows, a
    different key, or a different template?
12. Does a scheduled row ever appear OUTSIDE a Start/End block?

---

# PHASE 18-3-C — Known-Team Scheduled Search & Main Event Evidence

Observation window: **2026-09-30 (UTC)**. Objective: find a genuine
scheduled MatchSchedule with **populated team1/team2** (handoff section 5).
Outcome: **no known-team scheduled row is currently observable** — see
NETWORK ACTIVITY below. All evidence in this section is FACT (directly
observed in saved raw wikitext) unless labeled INFERENCE/UNKNOWN.
Deterministic tests: `tests/test_main_event_scheduled_schema.py`.

## Network Activity (this phase)

The phase began by resuming an interrupted prior attempt whose request #1
had already fetched `Data:2026 Season World Championship/Main Event`
(saved as `raw/leaguepedia/page_Data_2026 Season World Championship_Main
Event.wikitext` + response JSON; log: `phase18_3c_fetch_metadata.json`,
1 request, 0 retries, HTTP 200). A byte-identical duplicate pair with an
underscore filename (`..._Main_Event.wikitext`) from an unlogged earlier
fetch also exists in raw/ and was left untouched. This phase then made **one
discovery request** (`allpages` for Data-namespace pages prefixed
"2026 Season"; log: `phase18_3c_discovery_metadata.json`, HTTP 200):

```
Data:2026 Season World Championship/Main Event
Data:2026 Season World Championship/Play-In
```

Only these two 2026 Season Data pages exist, and both have EMPTY team slots
(Play-In: PHASE 18-3-B; Main Event: below). Per handoff section 22B,
network exploration stopped at the request budget. No rate-limit events,
no retries, no policy bypasses.

## Main Event Scheduled Evidence (all team slots empty)

`Data:2026 Season World Championship/Main Event`: **40 MatchSchedule rows,
ALL scheduled/unplayed** (dates 2026-10-23..2026-11-14, all future vs the
2026-09-30 observation; no row has winner/score values). 8 Start blocks:
Round 1/2 (bestof=1), Round 3/4/5 (bestof=3), Quarterfinals/Semifinals/
Finals (bestof=5).

MatchSchedule fields on these 40 rows: value-bearing keys = `date`, `time`,
`timezone`(PST, 40/40), `dst`, `initialorder`, `stream`; empty keys =
`team1`, `team2`, `team1score`, `team2score`, `winner`, `pbp`, `color`,
`vodinterview`, `with`, `mvp`, `vodhl`, `reddit`, `qq`. Game blocks per row
equal the applicable bestof (1/3/5); all game fields empty including
`riot_platform_game_id` (0 preassigned across all rows).

New structural facts vs PHASE 18-3-B (first observation anywhere):

1. **`qq` key**: present (empty) on all 40 rows — a key never seen in the
   LCK/Worlds-Play-In fixtures. Meaning UNKNOWN.
2. **Game key set differs across pages**: Main Event game templates use
   `recap` where the LCK and Play-In fixtures used `vod` (17 keys, single
   consistent set on this page). The PHASE 18-2 statement "MatchSchedule/Game
   key set was consistent" applies per-page, not globally.
3. **Series-level `bestof` override**: rows 17, 18, 21, 22 (tab=Round 3,
Start bestof=3) each carry `bestof=1` on the MatchSchedule row itself with
exactly 1 pre-created game block. First observed instance of a
series-level bestof differing from its Start (old Open Question 3,
partially answered: exceptions ARE marked with a row-level `bestof` key).
Note: the Road to MSI fixture (PHASE 18-3-A) also carried row-level
`bestof=5` matching its Start, so the key is not scheduled-specific —
but an OVERRIDE (1 vs 3) is first observed here, on scheduled rows.
4. **`dst` values beyond yes**: `dst=yes` (16 rows, 10-23..10-24),
`dst=spring` (17 rows, 10-25..10-31), `dst=no` (7 rows, 11-03..11-14).
Interpretation remains UNKNOWN (section DST below).

## Why No Known-Team Scheduled Match Was Found

FACT: both existing 2026 Season Data pages have empty team1/team2 on every
scheduled row. INFERENCE: Worlds 2026 participants were not yet determined
as of 2026-09-30 (Play-In runs 10-15..10-18), so no page can yet carry a
known-team scheduled series. KNOWN-TEAM SCHEDULED SCHEMA = **UNKNOWN**;
no evidence was fabricated.

## DST

Observed: timezone=PST on all 40 rows; dst=yes (10-23..24), dst=spring
(10-25..31), dst=no (11-03..14). Interpretation: **UNKNOWN** — the value
set {yes, spring, no} is recorded verbatim; no semantic is inferred.

## Postponed / Cancelled

Not observed; no status-like key on any row. Schema = UNKNOWN.

## Open Questions (added by PHASE 18-3-C)

13. What does the `qq` key mean, and does it ever carry a value?
14. Does the series-level `bestof` override also appear on COMPLETED rows
    (only a matching bestof=5 was observed on Road to MSI)?
15. What do `dst=yes/spring/no` mean on PST rows (note: US DST 2026 ends
    2026-11-01, near the yes/spring→no boundary 10-31→11-03 — coincidence
    not yet established; recorded as an observation, not a conclusion)?
16. Is the game-level `recap`-vs-`vod` key difference purely per-page
    convention, or does it follow event/organizer scope?

---

# PHASE 18-3-D-EMEA — Known-Team Scheduled Evidence (EMEA Masters 2026)

Observation timestamp: **2026-09-30T11:51Z** (fetch at ~2026-09-30T11:51Z).
Target page: `Data:EMEA Masters/2026 Season/Summer Main Event`. Network: **1
request** (action=query revisions, established path, HTTP 200, 0 retries, 0
rate-limit events, no bypasses). Raw fixture:
`raw/leaguepedia/page_EMEA_Masters_2026_Summer_Main_Event.wikitext` (+ response
JSON); metadata: `raw/leaguepedia/phase18_3d_emea_fetch_metadata.json`.
Deterministic tests: `tests/test_emea_known_team_scheduled.py`.
Everything below is FACT (directly observed) unless labeled INFERENCE/UNKNOWN.

## Page Overview

93 MatchSchedule rows across Start tabs Round 1–7 (Start `bestof=1` on all
tabs). Every row carries a row-level `bestof` key (1 or 3). State at
observation: rows 1–64 COMPLETED (09-26..09-29); **rows 65–78 = 14 genuine
KNOWN-TEAM SCHEDULED rows** (dates 2026-09-30, times 06:00–11:00 PST =
14:00–19:00 UTC at earliest, i.e. all after the 11:51Z observation even
under the alternate PDT reading — the classification is robust to the
unknown DST semantics); rows 79–93 = 15 future rows (10-01/10-02) with
`team1=TBD`, `team2=TBD`.

## Selected Rows (65–78) — Exact Observations

- `team1`/`team2` non-empty, `winner`/`team1score`/`team2score` empty (14/14)
- `timezone=PST`, `dst=yes`, `date=2026-09-30` on all 14 rows
- Game blocks: 6 BO1 rows × 1 game + 8 BO3 rows × 3 games = 30 blocks; every
  game field (blue, red, winner, rpgid, selections, vod/recap, mvp…) empty
- **Q1 answer — representation is MIXED, even within a single row**:
  codes (`BIG`, `SNSH`, `FEC`, `HMBLE`, `HRTS.A`, `KHK`, `GMCE`, `ESB`,
  `UOL.SE`, `TSC HR`), full names (`Bushido Wildcats`, `Otter Side`, `PCIFIC
  Esports`, `JSK Esports`, `Skillcamp`, `Colossal Gaming`, `Valerion`,
  `UCAM Esports`, `Bomba Team`, `Nightbirds`, `SU Esports`), and hybrid /
  short forms (`TLN Pirates`, `G2 NORD`, `Barca`, `Phantasma`, `Magaza`,
  `LODIS PL`). Example row 66: `team1=Bushido Wildcats` (full name) vs
  `team2=Magaza` (short form).
- **Q2 answer — rpgid**: OBSERVED_ABSENT on this page's scheduled rows
  (0/30 game blocks preassigned). Scoped to this page; completed rows on the
  same page DO carry `LOLTMNT05_*` rpgids (e.g. `LOLTMNT05_223266`), so the
  emptiness is a pre-match state, not a page-wide omission.
- **Q3 answer**: Game block count == row-level bestof on every row of the
  page (BO1→1, BO3→3; also true for completed and TBD rows).
- **Q4 answer**: row-level `bestof` overrides ARE OBSERVED here: Start
  `bestof=1` on all tabs, but 8 scheduled rows (71–78) + later rounds carry
  `bestof=3` with 3 game blocks. Additionally, EVERY row on this page has a
  row-level bestof (unlike the LCK fixtures where it was absent).
- **Q5 answer**: scheduled game `blue`/`red` are empty (OBSERVED_ABSENT), so
  team1-vs-blue comparison is not possible pre-match; on the same page's
  COMPLETED rows, blue/red use the same representation as the series
  team1/team2 (e.g. row 19 blue=`Senshi eSports (Benelux Team)`, a full
  name, matching that row's representation style).
- **Q6 answer**: UNKNOWN. The TBD rows show only that undetermined slots use
  the literal `TBD`. No raw evidence establishes any team1/team2 ordering
  semantics. (Ruleset context was provided but, per the evidence layers
  rule, cannot manufacture Leaguepedia field meaning.)

## Team Mapping Comparison

FACT: none of the 14 rows' team values appear in `config/team_mappings.json`
(that config covers LCK 2026 teams only). Classification per value:
OBSERVED (representation observed in raw source) but mapping UNKNOWN — no
mapping was created or modified.

## Additional First-Time Observations on This Page

1. **`TBD` placeholder** for undetermined scheduled teams (15 rows) — first
   observation of a non-empty placeholder representation.
2. **Forfeit representation (row 9, COMPLETED)**: row-level `ff=2` together
   with a new `team2footnote` key containing
   `"[[White Dragons]] failed to show up."` plus an external citation
   (`cargoref` to a Karmine Corp X post). winner=1, scores 1-0. Recorded
   verbatim; semantics of `ff` (beyond co-occurring with the footnote) NOT
   inferred.
3. Series-level key set adds `ff` and `team2footnote`; game-level key set
   uses the `recap` variant (like Worlds Main Event, unlike LCK `vod`).
4. Completed-row rpgids on this page use the `LOLTMNT05` prefix (LCK fixture
   used `LOLTMNT02`, Worlds Play-In evidence mentioned `LOLTMNT01`).

## DST

Observed: `timezone=PST`, `dst=yes` on all rows (including 2026-09-30 rows).
Interpretation: UNKNOWN (unchanged; no external research performed).

## Postponed / Cancelled

Not observed. (Forfeit observed — see above — but that is a completed-match
annotation, not a postponed/cancelled representation.) Still UNKNOWN.

## Is This Sufficient for Scheduled-Normalization Design?
Partially. Now observed: scheduled rows with known teams keep the same key
structure as completed rows; result fields stay empty; rpgid is not
preassigned (this page); game-block count follows row-level bestof; team
representation is MIXED (code/full-name/short per team, per row) and must
be resolved through the existing exact-match resolver with UNKNOWN
classification for unmapped names. Still missing before implementation:
whether team1/team2 ever change between scheduling and completion, whether
rpgid can appear mid-series pre-completion elsewhere, and DST semantics.

## Open Questions (added by PHASE 18-3-D-EMEA)

17. Does `TBD` get replaced by the real team value on the same row (row
    identity preserved), and does `initialorder` stay stable?
18. What does series-level `ff` encode exactly (forfeit side? count?), and
    is `team2footnote`/`team1footnote` a general annotation mechanism?
19. Are EMEA team representations stable between the scheduled row and its
    completed state (e.g. `Magaza` vs `Magaza Esports` observed on different
    rows of this page — same team, two spellings)?

---

# PHASE 18-3-C — Main Event Scheduled Evidence (Known-Team Target NOT Found)

Observation timestamp: **2026-09-30T10:40:07Z** (raw fixture
`raw/leaguepedia/page_Data_2026 Season World Championship_Main Event.wikitext`,
saved unmodified by the single permitted PHASE 18-3-C request; log in
`raw/leaguepedia/phase18_3c_fetch_metadata.json`; fetch tool
`tests/fetch_main_event.py`). Page title:
`Data:2026 Season World Championship/Main Event`.

Primary objective result: **KNOWN-TEAM SCHEDULED SCHEMA = UNKNOWN** — all 40
rows on this page have empty team1/team2, because as of the observation
timestamp no Main Event matchup existed yet (Play-In runs 2026-10-15..18;
Main Event starts 2026-10-23). Both Worlds Data pages fetched so far were
therefore unable to answer the known-team questions (handoff Q1-Q4 all
UNKNOWN). Per handoff section 22 stop condition B, network exploration
stopped without further requests.

The fixture still establishes NEW structural facts, all FACT (directly
observed) unless labeled otherwise. Deterministic tests:
`tests/test_main_event_scheduled_schema.py`.

## Observed Structure (40 rows, all genuinely scheduled)

8 `{{MatchSchedule/Start}}` blocks (Round 1/2 bestof=1; Round 3/4/5 bestof=3;
Quarterfinals/Semifinals/Finals bestof=5; `shownname=Worlds 2026 Main Event`)
and 40 `{{MatchSchedule}}` rows, every date 2026-10-23..2026-11-14 — all
future relative to the observation. All 40 rows: team1/team2/team1score/
team2score/winner OBSERVED_ABSENT (empty keys).

## NEW FACT 1: Per-row bestof override (first observation)

4 rows inside `tab=Round 3` (Start `bestof=3`) carry a **series-level
`bestof=1` argument** — the first series-level bestof ever observed in this
project (Rounds 3-4 fixture had none, 40/40). Raw shape:
`|bestof=1|initialorder= 3|team1= |...`. Game-block counts follow the
EFFECTIVE bestof in all 40 rows: bestof=1 rows have 1 game block, Round 3
rows without override have 3, Round 4/5 have 3, QF/SF/F have 5 (94 game
templates total). INFERENCE: a per-row bestof overrides the Start context
and the wiki pre-creates that many game blocks. UNKNOWN: whether the Start
value or the override wins for rendering in all wiki contexts.

## NEW FACT 2: dst has (at least) three observed values

Round 1/2 rows (2026-10-23/24): `dst=yes` (16 rows). Round 3/4/5 rows
(2026-10-25..31): `dst=spring` (17 rows) — a value never observed before in
this project. Quarterfinals/Semifinals/Finals rows (2026-11-03..14):
`dst=no` (7 rows). Interpretation: **UNKNOWN** — do not read dst by its name
or value; `yes` and `spring` coexist inside October, so a month/season rule
cannot be inferred from this page alone either.

## NEW FACT 3: Key sets are page-dependent

Every series row carries an additional empty `qq=` key (40/40) not present
on any previously captured page. Every game template carries an additional
empty `recap=` key (94/94): the game key set here has 18 keys vs the 17-key
set observed on LCK/Play-In pages. Consequence: parsers and schema tests
must not hard-code one universal game key set.

## RPGID

0/94 game templates carry a `riot_platform_game_id` (all empty). Because all
teams are also unknown on this page, the known-team rpgid question (handoff
Q4) remains **UNKNOWN** — this page only confirms: no rpgid preassignment on
a page where matchups are entirely undetermined.

## Comparison with PHASE 18-3-B (Play-In)

| Aspect | Play-In (18-3-B) | Main Event (18-3-C) |
|---|---|---|
| rows all scheduled | 6/6 | 40/40 |
| team1/team2 | empty | empty |
| rpgid | 0/30 | 0/94 |
| game blocks per row | 5 = Start bestof=5 | = effective bestof (1/3/5) |
| series-level bestof | absent | `bestof=1` on 4/40 rows (NEW) |
| dst values | yes only | yes / spring / no (NEW) |
| series keys | — | + empty `qq` (NEW) |
| game keys | 17 | 18 (+ empty `recap`) (NEW) |
| status-like key | none | none |

## Open Questions (added by PHASE 18-3-C)

13. What does `dst=spring` mean, and why do `yes`/`spring`/`no` coexist on
    one page spanning October and November dates?
14. Is the per-row `bestof` override also used on completed rows, or only on
    scheduled Swiss-stage rows?
15. Do `qq`/`recap` appear with values on completed pages, or are they
    scheduled/placeholder-only keys here?
16. (Still open from 18-3-B) team representation and rpgid preassignment
    once a matchup is known — not answerable as of 2026-09-30.

---

# PHASE 18-3-D-EMEA — Known-Team Scheduled Rows (EMEA Masters 2026 Summer Main Event)

Observation timestamp: **2026-09-30T11:51:00Z** (`phase18_3d_emea_fetch_metadata.json`).
Target: `Data:EMEA Masters/2026 Season/Summer Main Event`. Network: exactly
**1 request** (action=query/revisions, established UA, no retries, no rate
limit, HTTP 200). Raw fixture:
`raw/leaguepedia/page_EMEA_Masters_2026_Summer_Main_Event.wikitext` +
response JSON. Preservation note: the .wikitext file was written by the
collector in Windows text mode (CRLF translation, 56,932 file bytes vs
54,892 content chars); the response JSON preserves the verbatim content.
Deterministic tests: `tests/test_emea_known_team_scheduled.py`.

Everything below is OBSERVED (verbatim in the saved raw wikitext) unless
labeled OBSERVED_ABSENT / UNKNOWN / INFERENCE.

## Page Overview (93 MatchSchedule rows)

| Rows | Round | State | Dates |
|---|---|---|---|
| 1–64 | Round 1–4 | completed (winner+scores+rpgid) | 2026-09-26..29 |
| 65–78 | Round 5 | **KNOWN-TEAM SCHEDULED** (14 rows) | 2026-09-30 (same day as observation) |
| 79–93 | Round 6–7 | scheduled, `team1=TBD`/`team2=TBD` | 2026-10-01..02 |

Round 5 rows are future under BOTH plausible PST readings (UTC-8:
14:00–19:00 UTC; UTC-7: 13:00–18:00 UTC), all after 11:51Z — the
classification does not depend on the unknown dst semantics.

## Selected Row (row 65, verbatim structure)

```
{{MatchSchedule/Start|tab=Round 5 |bestof=1 |shownname=EM 2026 Summer Main Event }}
{{MatchSchedule|bestof=1 |initialorder=5|team1=BIG |team2=SNSH |team1score= |team2score= |winner=
|date=2026-09-30 |time=06:00 |timezone=PST |dst=yes |pbp= |color= |vodinterview= |with= |stream=https://www.twitch.tv/primeleague
|game1={{MatchSchedule/Game
|blue= |red= |winner= |first_sel= |ssel= |pick_sel= |first_pick= |ff=
|riot_platform_game_id=
|recap=
|vodpb= |vodstart= |vodpost= |vodhl= |vodinterview= |with= |mvp=
}}}}
```

## Q1 — team1/team2 Representation: MIXED, page-wide AND within single rows

OBSERVED raw values on the 14 known-team scheduled rows (verbatim, not
normalized): codes `BIG`, `SNSH`, `HMBLE`, `KHK`, `FEC`, `GMCE`, `ESB`,
`FSK`, `TSC HR`, `UOL.SE`, `LODIS PL`, `HRTS.A`, `KCB`; full names
`Bushido Wildcats`, `JSK Esports`, `PCIFIC Esports`, `Colossal Gaming`,
`Valerion`, `Otter Side`, `Ruddy Corporation`, `Nightbirds`, `Skillcamp`,
`UCAM Esports`, `Anubis Gaming`, `White Dragons`, `Bomba Team`,
`The Secret Club`; short forms `Barca`, `Magaza`; hybrid `G2 NORD`.
Within ONE row representations differ: row 66 `team1=Bushido Wildcats` vs
`team2=Magaza` (full name vs short form); row 73 `team1=HMBLE` vs
`team2=Barca` (code vs short form). The completed rows on the same page
use the same mixed style. INFERENCE: representation is per-editor-choice,
not per-state — there is no scheduled-vs-completed representation rule.
Mapping comparison: `config/team_mappings.json` is LCK-only; **none** of
these values appear in it → every value resolves UNKNOWN via the exact
resolver (fail-closed verified by tests). No mapping was created or
modified. Additional OBSERVED fact: the same page spells one team as
`Magaza Esports` (rows 32/43) and `Magaza` (rows 52/66), and another as
`Barça eSports` (row 23) vs `Barca` (rows 52/73) — multiple spellings
coexist; whether they denote the same team is UNRESOLVED (identity
resolution would require evidence, not string similarity).

## Q2 — rpgid Preassignment: OBSERVED_ABSENT (0/30)

All 30 pre-created game blocks on rows 65–78 have EMPTY
`riot_platform_game_id`. Scoped conclusion (no generalization): **no rpgid
was preassigned in these observed known-team scheduled series.** Scoping
check (OBSERVED): completed rows 1–64 DO carry rpgids (`LOLTMNT05_*`), so
emptiness is a pre-match state, not a page-wide convention.

## Q3 — Game Block Count = effective BestOf

OBSERVED: rows 65–70 (row `bestof=1`) have exactly 1 game block; rows
71–78 (row `bestof=3`) have exactly 3. Total 30 blocks / 14 rows. Effective
BestOf = row-level `bestof` (see Q4). Completed rows differ: their block
count equals games PLAYED (row 61: 0-2 sweep → 2 blocks; row 62: 1-2 →
3 blocks), consistent with LCK fixtures — pre-creation to full bestof is a
scheduled-row behavior.

## Q4 — Row-Level BestOf Override: OBSERVED on BOTH scheduled and completed rows

Every Round 5 Start carries `bestof=1`, yet rows 71–78 carry row-level
`bestof=3` (with 3 pre-created blocks) — override confirmed on scheduled
rows. Rows 61–64 (Round 4, completed) carry `bestof=3` against Start
`bestof=1` — override ALSO observed on completed rows (answers former open
question 14: overrides are not scheduled-specific).

## Q5 — team1/team2 vs blue/red

OBSERVED_ABSENT: all scheduled game blocks have EMPTY `blue`/`red` (no
pre-match side assignment). No relation between team1/team2 order and
sides can be observed from this page; none is inferred.

## Q6 — Ruleset Relationship (layers kept separate)

LAYER A (RULESET CONTEXT ONLY, provided by the user, not fetched this
phase): the Worlds 2026 Play-In rulebook statement "Teams will be drawn
into matches by random selection… The order of the draw will not determine
the order in which the matches are played."
LAYER B (LEAGUEPEDIA, OBSERVED): rows carry `initialorder=5,6,7,…` within
Round 5; team1/team2 contain the mixed representations above.
LAYER C: VALID statement — "rulesets may determine WHICH teams are paired;
the raw row shows team1=X, team2=Y." INVALID (not claimed) — "team1 is the
draw winner / higher seed / blue side." The meaning of `initialorder`
remains UNKNOWN.

## Bonus Observations (same page, in scope)

- **`TBD` placeholder (first observation)**: rows 79–93 use literal
  `team1=TBD` / `team2=TBD` with empty results and 3 pre-created blocks
  (row bestof=3 vs Start bestof=1 — more overrides). `TBD` is non-empty
  but is NOT a team identity; future normalization must treat it as its
  own state, never as a team code.
- **Forfeit representation (first observation)**: row 9 (completed):
  series-level `ff=2`, `winner=1`, score 1-0, `team2footnote` containing
  "failed to show up" with an external citation, and ZERO game blocks
  (0 rpgids). ff semantics beyond "team2 forfeited" are not inferred.
- Game key set: 18 keys including `recap` (matches Worlds Main Event,
  differs from LCK/Play-In 17-key set — page-dependence confirmed again).
- Series key set adds `ff` and `team2footnote` vs all previous fixtures.
- DST: `timezone=PST`, `dst=yes` on all 93 rows. Interpretation: UNKNOWN
  (unchanged project position).
- Postponed/cancelled: no status-like key observed; the forfeit row is the
  closest representation evidence but postponed/cancelled remain UNKNOWN.

## Q1–Q6 Answer Table

| Q | Result | Classification |
|---|---|---|
| Q1 team1/team2 representation | mixed: code / full name / short form / hybrid, varying within single rows | OBSERVED |
| Q2 rpgid preassigned | empty on all 30 scheduled game blocks (scoped to this page) | OBSERVED_ABSENT |
| Q3 game blocks vs bestof | blocks = row-level bestof (1 or 3); completed rows = games played | OBSERVED |
| Q4 bestof overrides | yes — row `bestof=3` under Start `bestof=1`, on scheduled AND completed rows | OBSERVED |
| Q5 team1/team2 vs blue/red | blue/red empty pre-match; no observable relation | OBSERVED_ABSENT |
| Q6 ruleset relationship | ruleset context recorded; no team1-order semantics established | UNKNOWN |

## Sufficiency for Scheduled-Normalization Design

INFERENCE: the evidence now covers both empty-slot and known-team scheduled
rows, TBD placeholders, row-level bestof overrides, and forfeit rows — but
all from 3 event pages, one league family absent (LCK scheduled rows), with
dst semantics and `initialorder` meaning unresolved. Sufficient to DESIGN a
fail-closed scheduled normalization proposal (states: completed /
scheduled-known / scheduled-TBD; no status field exists in raw source), NOT
sufficient to promote anything to canonical data yet.

## Open Questions (added by PHASE 18-3-D-EMEA)

17. Is `TBD` the universal placeholder for undetermined scheduled teams
    (vs empty slots on Worlds pages — two different conventions observed)?
18. What does `initialorder` mean (observed 1..8 across pages)?
19. Do `ff` / `team*footnote` appear on other event families, and is
    `ff` always accompanied by a footnote citation?
20. Why do Worlds pages pre-create blocks to full bestof while completed
    EMEA rows shrink to games played — is block count ever reaped on
    completion, or do Worlds BO3 sweeps also keep 3 blocks?
21. Does rpgid ever get preassigned anywhere (still unobserved), and at
    what point relative to match creation?

