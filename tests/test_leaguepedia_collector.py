"""Unit tests for the Leaguepedia collector's fetch/response handling.

All tests are offline: they either feed saved raw fixtures directly or use a
local stdlib HTTP server on 127.0.0.1. No external network is touched.

The real Leaguepedia API is exercised separately by manual integration runs
(see README); those runs are recorded in raw/leaguepedia/.
"""

from __future__ import annotations

import http.server
import json
import pathlib
import sys
import threading
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

from lib.fetch import (  # noqa: E402
    FetchError,
    HttpError,
    MalformedJsonError,
    QueryError,
    RateLimitedError,
    fetch_api_json,
    fetch_raw,
)

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class _Handler(http.server.BaseHTTPRequestHandler):
    routes: dict[str, tuple[int, str]] = {}

    def do_GET(self):  # noqa: N802
        code, body = self.routes.get(self.path, (404, "not found"))
        payload = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):  # silence test output
        pass


class LocalServer:
    """Minimal stdlib HTTP server bound to 127.0.0.1 on a random free port."""

    def __init__(self, routes: dict[str, tuple[int, str]]):
        self.routes = routes
        self._server = http.server.ThreadingHTTPServer(
            ("127.0.0.1", 0), type("H", (_Handler,), {"routes": routes})
        )
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self._server.server_address[1]}"

    def stop(self) -> None:
        self._server.shutdown()
        self._thread.join(timeout=5)
        self._server.server_close()


class NoSleep:
    """Records backoff delays instead of sleeping (keeps tests fast/deterministic)."""

    def __init__(self) -> None:
        self.delays: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.delays.append(seconds)


class FetchRawTests(unittest.TestCase):
    def test_success_200_returns_parsed_payload(self):
        server = LocalServer({"/api?x=1": (200, fixture("page_wikitext_200.json"))})
        try:
            result = fetch_raw(server.base_url + "/api?x=1")
        finally:
            server.stop()
        self.assertIsNotNone(result.body_json)
        self.assertIn("MatchSchedule", result.body_text)

    def test_http_404_raises_http_error_without_retry(self):
        server = LocalServer({"/missing": (404, "not found")})
        sleeper = NoSleep()
        try:
            with self.assertRaises(HttpError) as ctx:
                fetch_raw(server.base_url + "/missing", sleep_function=sleeper)
        finally:
            server.stop()
        self.assertEqual(404, ctx.exception.status)
        self.assertEqual([], sleeper.delays)  # HTTP errors are not retried

    def test_ratelimited_error_object_retries_with_backoff_then_gives_up(self):
        server = LocalServer({"/api": (200, fixture("cargoquery_ratelimited.json"))})
        sleeper = NoSleep()
        try:
            with self.assertRaises(RateLimitedError):
                fetch_raw(
                    server.base_url + "/api",
                    max_attempts=4,
                    initial_delay_seconds=1,
                    max_delay_seconds=30,
                    sleep_function=sleeper,
                )
        finally:
            server.stop()
        # 1s, 2s, 4s between the 4 attempts (exponential, capped at 30s)
        self.assertEqual([1.0, 2.0, 4.0], sleeper.delays)

    def test_ratelimited_recovers_when_server_starts_returning_data(self):
        state = {"calls": 0}

        class Flipping(_Handler):
            def do_GET(self):  # noqa: N802
                state["calls"] += 1
                if state["calls"] < 3:
                    body = fixture("cargoquery_ratelimited.json")
                    code = 200
                else:
                    body = fixture("page_wikitext_200.json")
                    code = 200
                payload = body.encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):  # noqa: N802 - silence daemon thread logs
                pass

        inner = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Flipping)
        thread = threading.Thread(target=inner.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{inner.server_address[1]}/api"
        sleeper = NoSleep()
        try:
            result = fetch_raw(
                url,
                initial_delay_seconds=0.0,
                sleep_function=sleeper,
            )
        finally:
            inner.shutdown()
            inner.server_close()
        self.assertIn("MatchSchedule", result.body_text)

    def test_mwexception_error_object_is_not_retried(self):
        server = LocalServer({"/api": (200, fixture("cargoquery_mwexception.json"))})
        sleeper = NoSleep()
        try:
            with self.assertRaises(QueryError) as ctx:
                fetch_raw(server.base_url + "/api", sleep_function=sleeper)
        finally:
            server.stop()
        self.assertEqual("internal_api_error_MWException", ctx.exception.code)
        self.assertEqual([], sleeper.delays)

    def test_malformed_json_raises_without_retry(self):
        server = LocalServer({"/api": (200, "{not json")})
        sleeper = NoSleep()
        try:
            with self.assertRaises(MalformedJsonError):
                fetch_raw(server.base_url + "/api", sleep_function=sleeper)
        finally:
            server.stop()
        self.assertEqual([], sleeper.delays)

    def test_connection_failure_raises_fetch_error_after_retries(self):
        """Deterministic transport-failure simulation (no real sockets):
        the injected http_get raises URLError(OSError('connection refused'))."""
        import urllib.error

        attempts = {"count": 0}

        def failing_get(url: str, timeout_seconds: float) -> str:
            attempts["count"] += 1
            raise urllib.error.URLError(
                OSError(10061, "connection refused", None, 10061)
            )

        sleeper = NoSleep()
        with self.assertRaises(FetchError):
            fetch_raw(
                "http://127.0.0.1:9/api",
                max_attempts=2,
                initial_delay_seconds=0.0,
                sleep_function=sleeper,
                http_get=failing_get,
            )
        self.assertEqual(2, attempts["count"])
        self.assertEqual([0.0], sleeper.delays)


class FetchApiJsonTests(unittest.TestCase):
    def test_api_json_returns_fetch_result_with_parsed_payload(self):
        server = LocalServer({"/api.php?action=cargotables&format=json": (200, '{"cargotables":["ScoreboardGames"]}')})
        try:
            result = fetch_api_json(
                server.base_url + "/api.php",
                {"action": "cargotables", "format": "json"},
                sleep_function=NoSleep(),
            )
        finally:
            server.stop()
        self.assertEqual(["ScoreboardGames"], result.body_json["cargotables"])
        self.assertIn("cargotables", result.body_text)

    def test_api_json_query_error_raises_query_error(self):
        server = LocalServer({"/api.php?action=cargoquery": (200, fixture("cargoquery_mwexception.json"))})
        try:
            with self.assertRaises(QueryError):
                fetch_api_json(server.base_url + "/api.php", {"action": "cargoquery"}, sleep_function=NoSleep())
        finally:
            server.stop()


class CollectorOutputTests(unittest.TestCase):
    def test_fixture_parse_page_wikitext_exposes_match_schedule_args(self):
        """The saved fixture represents the observed real page structure."""
        payload = json.loads(fixture("page_wikitext_200.json"))
        content = payload["query"]["pages"][0]["revisions"][0]["slots"]["main"]["content"]
        self.assertIn("{{MatchSchedule/Start|tab=Week 1 |bestof=3}}", content)
        self.assertIn("team1=T1", content)
        self.assertIn("riot_platform_game_id=LOLTMNT02_000001", content)


if __name__ == "__main__":
    unittest.main()
