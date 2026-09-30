# PHASE 17 — Normalization Report

- 실행 일시: 2026-09-29
- 실행 명령: `python scripts/normalize_sample.py` (venv: Python 3.13.15)
- 입력 fixture: `raw/leaguepedia/page_data_lck_rounds34.wikitext` (54,964 bytes, `Data:LCK/2026 Season/Rounds 3-4`)
- 출력: `data/matches.sample.json` (SAMPLE / PHASE 17 / production 아님)

## 1. Parser 실행 결과

| 항목 | 값 | Confidence |
|---|---|---|
| `{{MatchSchedule/Start}}` 블록 | 4개 (Week 10, 11, 12, 13 — 모두 `bestof=3`) | OBSERVED |
| `{{MatchSchedule}}` 시리즈 블록 | 40개 | OBSERVED |
| `{{MatchSchedule/Game}}` 게임 블록 | 99개 | OBSERVED |
| winner 없는 시리즈 | 0개 | OBSERVED |
| score 없는 시리즈 | 0개 | OBSERVED |
| 관측된 팀 코드 | 10개 (`BNK FEARX, DN SOOPers, DPLUS, GEN, HANJIN BRION, HLE, KRX, KT, NS, T1`) | OBSERVED |
| 관측된 timezone | `KST` 단일 (dst=`yes` 전 행) | OBSERVED |

균형 템플릿 파서가 중첩(`MatchSchedule/Game`이 `MatchSchedule` 인자 안에 중첩), `[[link|text]]` 파이프,
`<!-- -->` 주석, 값 내 `=`(VOD URL)를 모두 정확히 처리함 — parser 단위 테스트 17개로 검증.

## 2. 샘플 범위와 정규화 결과

| 항목 | 값 |
|---|---|
| 샘플 범위 | 첫 Start 블록(Week 10)의 시리즈만 |
| 정규화 성공 | **10개** |
| 제외 | **0개** |
| timezone 경고가 붙은 record | 10개 (전부 `dst=yes`-KST 모순 경고, 레코드는 유지) |
| record-level validator problems | **0개** |

## 3. Timezone 정규화

- 경로: `zoneinfo(Asia/Seoul)` 시도 → 이 환경은 `tzdata` 부재로 실패(Windows) →
  `config/timezone_offsets.json`의 검증된 고정 오프셋(KST = +540분, 서머타임 없음)으로 폴백.
- 검증(실측): `2026-07-29 17:00 KST → 2026-07-29T08:00:00Z`, `2026-08-02 19:00 KST → 2026-08-02T10:00:00Z`.
- **경고(10건, 전 행)**: fixture의 `dst=yes` 플래그는 "KST는 DST를 사용하지 않는다"는 IANA 사실과 모순.
  오프셋 계산에 플래그를 사용하지 않고 경고로 기록함 — flag의 실제 의미는 UNKNOWN.
- CET/CEST: 게임 레벨(Scoreboard)에서만 관측되었고 canonical 승격 대상이 아니므로 매핑하지 않음(의도).

## 4. Status 매핑

- `completed`: winner(숫자) + team1score/team2score(숫자)가 **모두 관측된** 시리즈에만 부여 — 본 샘플 10개 전부 해당.
- `scheduled`/`in_progress`/`postponed`/`cancelled`/`unknown`: **미관측** → 매핑 규칙 없음.
  "시간이 지났으니 completed", "score가 없으니 scheduled" 같은 추론은 하지 않음. (지시 §12)

## 5. BestOf 처리

- `{{MatchSchedule/Start|bestof=3}}`은 **탭(주차) 단위** 값이며 시리즈별 필드가 아님 (OBSERVED).
- canonical 포함 조건을 다음과 같이 검증: `team1score+team2score(플레이된 게임 수) ≤ bestof` —
  샘플 10개 전부 통과(2-0, 2-1만 존재) → bestOf=3 포함(근거: 탭 컨텍스트 + 스코어 정합성, `_provisional.bestOfSource` 기록).
- 시리즈별 예외(예: 타이브레이커 BO1) 존재 여부는 **미확인** — 전체 규칙은 미완성 상태로 남김.

## 6. Team mapping / ID

- 관측된 팀 코드 10개와 TournamentGroups의 팀 이름 10개는 각각 CONFIRMED이나,
  **코드↔이름 1:1 대응은 2건만 검증**(KRX↔Kiwoom DRX, NS↔Nongshim RedForce — 같은 날짜/대진의
  Scoreboards 풀네임과 일치). 나머지 8건은 UNRESOLVED.
- canonical team ID는 **미확정** → normalizer는 관측된 코드 자체를 provisional id로 사용
  (`_provisional.teamIdSource` 기록). `config/team_mappings.json`에 전체 상태 기록.
- 시리즈 ID: 공식 시리즈 ID가 관측되지 않아 **deterministic synthetic ID**
  `lp:<tournament>:<date>:<code1>:<code2>` 사용(중복 시 `:02` 이후 접미사 — 본 샘플에서는 중복 없음).
  `_provisional.idType` 기록.

## 7. Validator 결과

- record-level: 10개 전부 통과 (`validate_match` — id/league/tournament/stage/teamIds/scheduledAt(ISO-8601 UTC)/status/bestOf/score/sources/lastUpdatedAt).
- envelope-level: **promotion BLOCKED** — canonical team ID 미확정 + 전체 리그/팀 목록 미구축.
  `data/matches.sample.json`의 `_meta.envelopePromotion: BLOCKED`로 기록.
  `validate_envelope` 자체는 단위 테스트 9개로 검증(정상/오류 케이스).

## 8. UNKNOWN / 보류 목록

- 예정(scheduled) 경기 row 구조 — fixture에 미관측
- BestOf 시리즈별 예외 규칙
- 팀 코드↔이름 8건 + canonical 팀 ID 전체
- `cargoquery` row 스키마 (rate limit으로 미확보)
- `dst=yes` 플래그의 실제 의미 (KST와 모순)
- ScoreboardGames Cargo row의 시리즈 스코어 필드명
- 게임 레벨 팀 통계 약어의 정확한 의미(g/k/t/b 등 — 값은 관측, 의미는 INFERRED)

## 9. 대상 외 확인

- raw fixture 파일: 무변경 (읽기만 수행)
- policy snapshot: 무변경 (PHASE 16 상태 유지)
- Android 프로젝트: 무변경 (kt 파일 마지막 수정 시각 = PHASE 12 시점)
- `data/`에는 샘플 1개 파일만 생성 (production 대량 생성 없음)
