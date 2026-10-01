# Production Contract Gate (PHASE 18-17)

자동화된 production canonical 데이터 회귀/계약 게이트. 실수로 인한 데이터 손상,
롤백, 계약 드리프트를 조용히 수용하지 않고 **실패로 loudly 알린다**.

## Purpose

`data/matches.json`(production canonical JSON)이 내부적으로 일관되고, 기존
validator를 통과하며, 승인된 production baseline에서 벗어나지 않았는지
오프라인으로 검증한다.

## Offline contract test

```
# 전체 스위트 (오프라인, 게이트 포함)
.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py"

# 게이트만 직접 실행
.venv/Scripts/python.exe -m unittest tests.test_production_contract -v
```

- 네트워크/GitHub/Android/외부 패키지/자격 증명 불필요 (stdlib + 저장소 lib만 사용).
- `data/matches.json`을 직접 읽는다.
- 기존 validator(`lib.validator.validate_envelope` / `validate_match` /
  `validate_scheduled_match`)를 **재사용**한다 — 규칙을 복제하지 않는다.
- EMEA 변환 검증은 기존 DST-aware 로직(`lib.timezones.normalize_local_to_utc`)을
  재사용한다.

## Three-tier design

### 1. Immutable invariants (절대 완화 금지 — FAIL = 데이터 손상)

- envelope 필수 키 존재, `schemaVersion == 1`
- league/team/match ID unique
- non-null 팀 참조의 dangling 없음
- 기존 validator가 전 행 통과 (errors, warnings 모두 0)
- scheduled 행 score == null
- sources = `{source, kind, ref}` non-empty 문자열
- synthetic provenance 없음: top-level rpgid 필드 없음, scheduled 행
  `rpgidCount.nonEmpty == 0`, SampleData 오염 없음 (`sample`/플레이스홀더 리그)
- 팀: `team-` ID 규약, 필수 필드 non-empty, canonical 이름 unique
- EMEA 행의 `timeRaw`(timezone/dst)와 `utcConversion` 보존 + scheduledAt이
  기존 변환 로직으로 재계산한 값과 일치 (EMEA 리그 행에만 스코프)
- generatedAt / non-null scheduledAt: ISO-UTC Z
- lastUpdatedAt: `YYYY-MM-DD` 또는 ISO-Z (아래 known condition 참조)

### 2. Current production baseline (승인된 promotion에서만 갱신)

`tests/test_production_contract.py` 상단의 `BASELINE` 블록. 현재 값
(PHASE 18-17 승인, commit `b67121e`):

| 항목 | 값 |
|---|---|
| dataVersion | 2026.10.01.02 |
| leagues / teams / matches | 3 / 38 / 75 |
| completed / scheduled | 40 / 35 |
| bestOf | BO1 6, BO3 63, BO5 6 |
| 리그별 경기 | LCK 40, EMEA Masters 29, World Championship 6 |
| 리그 ID | LCK21, EM, Worlds |
| 팀 지역 | KR 10, EMEA 28 |
| EMEA scheduled | KNOWN 14 / TBD 15 |
| Worlds scheduled | 6 (unresolved, timezone pending) |
| lastUpdatedAt 혼합 | date-only 46 / ISO-Z 29 |

이 값들은 **보편적 스키마 불변식이 아니다** — 승인된 production 변경의 일부로만
갱신한다. **실패하는 테스트를 조용히 통과시키려고 baseline을 바꾸는 것은 금지.**

### 3. Intentionally mutable values

- `dataVersion`: 명시적 파서(`parse_version`, YYYY.MM.DD.NN)로 **형식 + baseline
  이상(monotonic)** 만 검사 → 정당한 미래 bump는 이 파일 수정 없이 통과,
  사고성 rollback은 즉시 FAIL.
- `generatedAt`: 형식만 검사 (동일성 단정하지 않음).

## dataVersion policy

promotion이 dataVersion을 올리면 BASELINE의 `dataVersion`도 그 promotion의
일부로 올린다. 게이트는 `dataVersion >= BASELINE`만 요구하므로 정상 bump는
추가 수정 없이 통과한다.

## EMEA regression contract

현재 29행 (KNOWN 14 / TBD 15)에만 적용. timeRaw(timezone=PST, dst=yes)와
`utcConversion=CONVERTED` 보존, scheduledAt이 기존 DST-aware 변환(PST+dst=yes →
UTC-07:00)과 일치하는지 검사. **다른 리그에 PST를 요구하지 않는다.**

## Worlds pending contract

현재 6행: 팀 슬롯/score/scheduledAt 전부 null, slotState EMPTY,
`utcConversion=PENDING_TIMEZONE_REVIEW`. 시간대는 여전히 미결(pending)이며,
승인된 Worlds timezone 연구가 완료될 때까지 이 상태가 유지되어야 함을 게이트가
보장한다.

## lastUpdatedAt mixed legacy format (known condition)

감사(18-17) 결과: LCK 40 + Worlds 6 = **46행은 date-only `2026-09-29`**
(18-9 시대 값), EMEA 29행은 ISO-Z(18-15 갱신분). 게이트는 두 형식을 모두
허용하고 혼합 분포를 baseline으로 기록한다. 임의의 타임스탬프 문자열은 FAIL.
다음 정당한 promotion에서 해당 행이 다뤄질 때 ISO-Z로 정규화하는 것을 권장
(별도 승인 필요, 이 게이트가 강제하지 않음).

## Remote smoke check (manual release gate)

```
python scripts/release_remote_check.py
```

- GitHub Pages production URL을 fetch → HTTP 200 + JSON 파싱.
- **원격 문서 == 로컬 `data/matches.json`** (파싱된 의미적 동등 비교).
- 동일한 오프라인 계약 게이트(`collect_problems`)를 원격 문서에 실행.
- dataVersion 형식/기준 대비 확인.
- 실패 시 non-zero exit. **unittest 스위트에 네트워크를 추가하지 않는다**
  (`test_` 접두사가 아니므로 자동 발견 제외).

## Promotion workflow

정당한 production promotion은 다음을 변경할 수 있다: dataVersion, generatedAt,
match count, status distribution, team count, league distribution.

의도적으로 변경할 때의 체크리스트:

1. canonical 데이터를 재생성/검증한다 (기존 validator + 전체 테스트).
2. 일반 테스트 스위트를 실행한다.
3. `tests/test_production_contract.py`의 **BASELINE 블록을 갱신**한다.
4. production contract test를 실행한다.
5. Pages 배포 후 `scripts/release_remote_check.py`를 실행한다.
6. 해당하면 Android E2E를 확인한다.

**baseline은 실패하는 테스트를 조용히 통과시키기 위해 절대 조용히 변경하지
않는다.**
