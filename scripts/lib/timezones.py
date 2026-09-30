"""Timezone abbreviation → UTC conversion.

The Leaguepedia fixture records match times as
``date=2026-07-29 |time=17:00 |timezone=KST |dst=yes`` — a *local* wall time
with a timezone *abbreviation*, which is inherently ambiguous (the same
abbreviation can mean different offsets, and DST flags change offsets).

Policy (per PHASE 17 rules): only abbreviations with an explicitly curated,
human-reviewable offset entry in ``config/timezone_offsets.json`` are converted.
Any other abbreviation produces a warning and the record stays out of the
canonical sample. ``zoneinfo`` is attempted first when the mapping lists IANA
candidates; on platforms without a tz database (Windows without the `tzdata`
package) the curated fixed offsets are used instead — the mapping file records
the source of each offset.
"""

from __future__ import annotations

import datetime
import json
import pathlib
from dataclasses import dataclass

CONFIG_PATH = pathlib.Path(__file__).resolve().parents[2] / "config" / "timezone_offsets.json"


@dataclass(frozen=True)
class TimeResult:
    utc_iso: str  # e.g. "2026-07-29T08:00:00Z"
    used_zoneinfo: bool
    warnings: list[str]


def _load_offsets() -> dict:
    if not CONFIG_PATH.exists():
        # test environments may run from a copied tree without config/
        alt = pathlib.Path(__file__).resolve().parents[1] / "config" / "timezone_offsets.json"
        if alt.exists():
            with open(alt, encoding="utf-8") as handle:
                return json.load(handle)
        raise FileNotFoundError(CONFIG_PATH)
    with open(CONFIG_PATH, encoding="utf-8") as handle:
        return json.load(handle)


def _zoneinfo_offset_minutes(iana_name: str, local: datetime.datetime) -> int | None:
    try:
        import zoneinfo  # noqa: PLC0415
    except ImportError:  # pragma: no cover
        return None
    try:
        tz = zoneinfo.ZoneInfo(iana_name)
    except Exception:  # ZoneInfoNotFoundError etc. (Windows without tzdata)
        return None
    offset = local.replace(tzinfo=tz).utcoffset()
    return None if offset is None else int(offset.total_seconds() // 60)


def normalize_local_to_utc(
    date_str: str,
    time_str: str,
    timezone_abbr: str,
    dst_flag: str,
    *,
    offsets: dict | None = None,
) -> TimeResult | None:
    """Convert a fixture local time to UTC ISO-8601.

    Returns None when the abbreviation is not in the curated mapping (caller
    must keep the record out of canonical data and record a warning).
    """
    warnings: list[str] = []
    table = offsets if offsets is not None else _load_offsets()
    entry = table.get(timezone_abbr.strip())
    if entry is None:
        return None

    local = datetime.datetime.fromisoformat(f"{date_str.strip()}T{time_str.strip()}:00")

    offset_minutes: int | None = None
    used_zoneinfo = False
    for iana in entry.get("ianaCandidates", []):
        candidate = _zoneinfo_offset_minutes(iana, local)
        if candidate is not None:
            offset_minutes = candidate
            used_zoneinfo = True
            break

    if offset_minutes is None:
        offset_minutes = int(entry["standardOffsetMinutes"])

    # dst flag cross-check: only meaningful for zones that actually have DST.
    has_dst_offsets = entry.get("dstOffsetMinutes") is not None
    dst = dst_flag.strip().lower() == "yes"
    if dst and not has_dst_offsets:
        warnings.append(
            f"dst flag is '{dst_flag.strip()}' but {timezone_abbr} is a fixed-offset zone "
            "in the curated mapping; the flag was ignored for the offset computation"
        )

    utc = local - datetime.timedelta(minutes=offset_minutes)
    return TimeResult(
        utc_iso=utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        used_zoneinfo=used_zoneinfo,
        warnings=warnings,
    )
