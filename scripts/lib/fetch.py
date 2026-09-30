"""Shared HTTP fetching helpers for the lol-esports-data collectors.

Standard library only. Provides:
- typed exceptions: HttpError, QueryError, RateLimitedError, MalformedJsonError
- fetch_raw(): GET returning a FetchResult (raw text + parsed JSON) with
  exponential backoff, honoring HTTP status codes and MediaWiki/Cargo JSON
  error objects (e.g. {"error": {"code": "ratelimited"}}).
- fetch_api_json(): fetch_raw() for a MediaWiki action URL; returns FetchResult.

Retry policy (observed behaviour, not an official limit):
- retry delays: 1s, 2s, 4s, 8s, then capped at 30s; hard attempt limit
- retryable: "ratelimited" JSON error objects and network failures (URLError)
- NOT retried: HTTP errors (e.g. 403/404/500), other API error objects
  (e.g. internal_api_error_MWException), malformed JSON
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

USER_AGENT = (
    "LoLEsportsFanDataCollector/0.1 "
    "(unofficial fan project; personal non-commercial)"
)

INITIAL_DELAY_SECONDS = 1.0
MAX_DELAY_SECONDS = 30.0
MAX_ATTEMPTS = 6


class FetchError(Exception):
    """Base class for collector fetch failures."""


class HttpError(FetchError):
    """Non-200 HTTP status (not retried)."""

    def __init__(self, status: int, url: str):
        self.status = status
        self.url = url
        super().__init__(f"HTTP {status} from {url}")


class QueryError(FetchError):
    """API returned a JSON error object other than ratelimited (not retried)."""

    def __init__(self, code: str, info: str, url: str):
        self.code = code
        self.info = info
        self.url = url
        super().__init__(f"API error {code}: {info} ({url})")


class RateLimitedError(FetchError):
    """API returned ratelimited and retries were exhausted."""

    def __init__(self, url: str, attempts: int):
        self.url = url
        self.attempts = attempts
        super().__init__(f"ratelimited after {attempts} attempts ({url})")


class MalformedJsonError(FetchError):
    """Response body was not valid JSON (not retried)."""


@dataclass(frozen=True)
class FetchResult:
    """Raw outcome of one successful (2xx, no error object) fetch."""

    url: str
    body_text: str
    body_json: object


def build_url(base: str, params: dict[str, str] | None = None) -> str:
    """Join a base URL with query parameters (properly encoded)."""
    if not params:
        return base
    return base + "?" + urllib.parse.urlencode(params)


def _http_get(url: str, timeout_seconds: float) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        if response.status != 200:
            raise HttpError(response.status, url)
        return response.read().decode("utf-8", errors="replace")


def _parse_json_and_check_errors(body_text: str, url: str) -> object:
    """Parse JSON; raise RateLimitedError for ratelimited, QueryError for any
    other API error object, MalformedJsonError for unparseable bodies."""
    try:
        payload = json.loads(body_text)
    except json.JSONDecodeError as exc:
        raise MalformedJsonError(f"malformed JSON from {url}: {exc}") from exc

    if isinstance(payload, dict) and isinstance(payload.get("error"), dict):
        error = payload["error"]
        code = str(error.get("code", "unknown"))
        info = str(error.get("info", ""))
        if code == "ratelimited":
            raise RateLimitedError(url, attempts=0)
        raise QueryError(code, info, url)
    return payload


def fetch_raw(
    url: str,
    *,
    max_attempts: int = MAX_ATTEMPTS,
    initial_delay_seconds: float = INITIAL_DELAY_SECONDS,
    max_delay_seconds: float = MAX_DELAY_SECONDS,
    timeout_seconds: float = 30.0,
    sleep_function=time.sleep,
    http_get=_http_get,
) -> FetchResult:
    """GET a URL with exponential backoff on retryable failures.

    Retryable: ratelimited JSON error objects, network failures (URLError).
    Non-retryable: HTTP errors, other API error objects, malformed JSON.

    ``http_get`` is injectable so tests can simulate transport failures
    (e.g. connection refused) deterministically without real sockets.
    """
    attempt = 0
    delay = initial_delay_seconds
    last_retryable_error: Exception | None = None
    while attempt < max_attempts:
        attempt += 1
        try:
            body_text = http_get(url, timeout_seconds=timeout_seconds)
        except urllib.error.HTTPError as exc:
            # HTTPError subclasses URLError — translate it BEFORE the URLError
            # handler so it is classified as an HTTP status, not a network error.
            raise HttpError(exc.code, url) from exc
        except urllib.error.URLError as exc:
            # connection refused / DNS / timeout — retryable network failure
            last_retryable_error = FetchError(f"network error for {url}: {exc.reason}")
            if attempt < max_attempts:
                sleep_function(delay)
                delay = min(delay * 2, max_delay_seconds)
                continue
            raise last_retryable_error from exc

        try:
            payload = _parse_json_and_check_errors(body_text, url)
        except RateLimitedError:
            last_retryable_error = RateLimitedError(url, attempts=attempt)
            if attempt < max_attempts:
                sleep_function(delay)
                delay = min(delay * 2, max_delay_seconds)
                continue
            raise last_retryable_error from None

        return FetchResult(url=url, body_text=body_text, body_json=payload)

    raise last_retryable_error if last_retryable_error else FetchError(
        f"failed after {attempt} attempts ({url})"
    )


def fetch_api_json(
    base_api_url: str,
    params: dict[str, str],
    *,
    max_attempts: int = MAX_ATTEMPTS,
    initial_delay_seconds: float = INITIAL_DELAY_SECONDS,
    max_delay_seconds: float = MAX_DELAY_SECONDS,
    timeout_seconds: float = 30.0,
    sleep_function=time.sleep,
) -> FetchResult:
    """GET a MediaWiki/Cargo API action URL; returns FetchResult so callers
    can use both the verbatim body text (raw storage) and parsed JSON."""
    return fetch_raw(
        build_url(base_api_url, params),
        max_attempts=max_attempts,
        initial_delay_seconds=initial_delay_seconds,
        max_delay_seconds=max_delay_seconds,
        timeout_seconds=timeout_seconds,
        sleep_function=sleep_function,
    )
