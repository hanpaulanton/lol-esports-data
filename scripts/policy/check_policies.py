"""Policy change checker (fail-closed).

For every config/policies/<source>.json this script:
1. Fetches the declared termsUrl.
2. Records a policy snapshot under policy_snapshots/<source>/<date>.json with
   {checkedAt, source, termsUrl, contentHash, observedStatus}.
3. Compares the hash with the most recent previous snapshot.

Exit codes (designed for CI, PHASE 19 will wire this up):
    0  OK / BASELINE recorded / SOURCE_UNAVAILABLE (collection must not run
       until a human reviews, but no terms change was observed)
    1  POLICY_CHANGED — terms content differs from the previous snapshot.
       Collection must STOP and a human must review.

Rules (see docs/policy-event-model.md):
- A terms change is never auto-accepted.
- An unavailable terms page is recorded as SOURCE_UNAVAILABLE, not as a change.
- Existing canonical data is never deleted because of a policy event.

The body hash is computed on the exact bytes returned; when a page is
client-rendered the hash therefore covers the served shell, and any
"UNRENDERED_PAGE" note in the policy file means the text content must also be
reviewed manually in a browser.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
import sys
import urllib.error
import urllib.request

USER_AGENT = (
    "LoLEsportsFanDataCollector/0.1 (unofficial fan project; personal non-commercial)"
)

STATUS_OK = "OK"
STATUS_BASELINE = "BASELINE"
STATUS_CHANGED = "POLICY_CHANGED"
STATUS_UNAVAILABLE = "SOURCE_UNAVAILABLE"


def load_policy_files(policy_dir: pathlib.Path) -> list[pathlib.Path]:
    return sorted(policy_dir.glob("*.json"))


def fetch_terms(url: str, timeout_seconds: float = 30.0) -> tuple[str | None, int | None]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            if response.status != 200:
                return None, response.status
            return response.read().decode("utf-8", errors="replace"), response.status
    except urllib.error.HTTPError as exc:
        return None, exc.code
    except urllib.error.URLError as exc:
        print(f"network error fetching {url}: {exc.reason}", file=sys.stderr)
        return None, None


def latest_snapshot_hash(snapshot_dir: pathlib.Path, source: str) -> tuple[str | None, str | None]:
    source_dir = snapshot_dir / source
    if not source_dir.exists():
        return None, None
    snapshots = sorted(source_dir.glob("*.json"))
    if not snapshots:
        return None, None
    latest = snapshots[-1]
    try:
        data = json.loads(latest.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None, str(latest)
    return data.get("contentHash"), str(latest)


def write_snapshot(
    snapshot_dir: pathlib.Path,
    source: str,
    terms_url: str,
    content_hash: str | None,
    observed_status: str,
) -> pathlib.Path:
    source_dir = snapshot_dir / source
    source_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    snapshot_path = source_dir / f"{today}.json"
    snapshot = {
        "checkedAt": datetime.datetime.now(datetime.timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "source": source,
        "termsUrl": terms_url,
        "contentHash": content_hash,
        "observedStatus": observed_status,
    }
    snapshot_path.write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return snapshot_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check external source policy changes (fail-closed)")
    parser.add_argument("--policy-dir", default="config/policies")
    parser.add_argument("--snapshot-dir", default="policy_snapshots")
    args = parser.parse_args(argv)

    policy_dir = pathlib.Path(args.policy_dir)
    snapshot_dir = pathlib.Path(args.snapshot_dir)
    files = load_policy_files(policy_dir)
    if not files:
        print(f"no policy files found in {policy_dir}", file=sys.stderr)
        return 1

    exit_code = 0
    for policy_path in files:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        source = policy["source"]
        terms_url = policy["termsUrl"]

        body, status = fetch_terms(terms_url)
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

        if body is None:
            observed = STATUS_UNAVAILABLE
            content_hash = None
            print(f"{source}: {observed} (HTTP {status}, terms not fetched; collection stays paused for review)")
            write_snapshot(snapshot_dir, source, terms_url, content_hash, observed)
            # Unavailable is not a change; the human-review requirement is
            # tracked by the snapshot. CI policy for this state is a warning.
            continue

        content_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
        previous_hash, previous_snapshot = latest_snapshot_hash(snapshot_dir, source)

        if previous_hash is None:
            observed = STATUS_BASELINE
            print(f"{source}: {observed} recorded (hash={content_hash[:12]}...)")
            exit_code = min(exit_code, 0)
        elif content_hash == previous_hash:
            observed = STATUS_OK
            print(f"{source}: {observed} (hash unchanged)")
        else:
            observed = STATUS_CHANGED
            print(
                f"{source}: {observed} — terms content differs from {previous_snapshot}. "
                "STOP collection; human review required.",
                file=sys.stderr,
            )
            exit_code = 1

        write_snapshot(snapshot_dir, source, terms_url, content_hash, observed)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
