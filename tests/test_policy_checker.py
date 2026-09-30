"""Unit tests for the policy checker (fail-closed behaviour)."""

from __future__ import annotations

import http.server
import json
import pathlib
import sys
import threading
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

from policy import check_policies  # noqa: E402


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


class PolicyCheckerTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(__file__).resolve().parent / ".tmp-policy"
        self.tmp.mkdir(exist_ok=True)
        (self.tmp / "policies").mkdir(exist_ok=True)
        (self.tmp / "snapshots").mkdir(exist_ok=True)

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_policy(self, source: str, terms_path: str, terms_url: str):
        policy = {
            "source": source,
            "termsUrl": terms_url,
            "lastReviewedAt": "2026-09-29",
            "policyStatus": "active",
            "collectionAllowed": True,
            "notes": "test policy",
        }
        (self.tmp / "policies" / f"{source}.json").write_text(
            json.dumps(policy), encoding="utf-8"
        )

    def start_server(self, routes):
        server = http.server.ThreadingHTTPServer(
            ("127.0.0.1", 0), type("H", (_Handler,), {"routes": routes})
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self._last_server = server
        self._last_thread = thread
        self.addCleanup(self._stop_last_server)
        return f"http://127.0.0.1:{server.server_address[1]}"

    def _stop_last_server(self):
        self._last_server.shutdown()
        self._last_thread.join(timeout=5)
        self._last_server.server_close()

    def snapshot_status(self, source: str) -> str:
        path = self.tmp / "snapshots" / source / "2026-01-01.json"
        # snapshots are dated with today; find whatever exists
        files = sorted((self.tmp / "snapshots" / source).glob("*.json"))
        if not files:
            return "NO-SNAPSHOT"
        return json.loads(files[-1].read_text(encoding="utf-8"))["observedStatus"]

    def test_first_run_records_baseline_and_exits_zero(self):
        base = self.start_server({"/terms": (200, "terms v1")})
        self.write_policy("testsrc", "/terms", base + "/terms")
        code = check_policies.main(
            ["--policy-dir", str(self.tmp / "policies"), "--snapshot-dir", str(self.tmp / "snapshots")]
        )
        self.assertEqual(0, code)
        self.assertEqual("BASELINE", self.snapshot_status("testsrc"))

    def test_unchanged_terms_exit_zero_with_ok_status(self):
        base = self.start_server({"/terms": (200, "terms v1")})
        self.write_policy("testsrc", "/terms", base + "/terms")
        check_policies.main(
            ["--policy-dir", str(self.tmp / "policies"), "--snapshot-dir", str(self.tmp / "snapshots")]
        )
        code = check_policies.main(
            ["--policy-dir", str(self.tmp / "policies"), "--snapshot-dir", str(self.tmp / "snapshots")]
        )
        self.assertEqual(0, code)
        self.assertEqual("OK", self.snapshot_status("testsrc"))

    def test_changed_terms_exit_one_with_policy_changed(self):
        routes = {"/terms": (200, "terms v1")}
        base = self.start_server(routes)
        self.write_policy("testsrc", "/terms", base + "/terms")
        check_policies.main(
            ["--policy-dir", str(self.tmp / "policies"), "--snapshot-dir", str(self.tmp / "snapshots")]
        )
        # terms content changes on the same server
        routes["/terms"] = (200, "terms v2 CHANGED")
        code = check_policies.main(
            ["--policy-dir", str(self.tmp / "policies"), "--snapshot-dir", str(self.tmp / "snapshots")]
        )
        self.assertEqual(1, code)
        self.assertEqual("POLICY_CHANGED", self.snapshot_status("testsrc"))

    def test_unavailable_terms_are_recorded_without_change_exit(self):
        routes = {"/terms": (200, "terms v1")}
        base = self.start_server(routes)
        self.write_policy("testsrc", "/terms", base + "/terms")
        check_policies.main(
            ["--policy-dir", str(self.tmp / "policies"), "--snapshot-dir", str(self.tmp / "snapshots")]
        )
        # terms page becomes unavailable (e.g. Cloudflare 403 like Liquipedia)
        routes["/terms"] = (403, "forbidden")
        code = check_policies.main(
            ["--policy-dir", str(self.tmp / "policies"), "--snapshot-dir", str(self.tmp / "snapshots")]
        )
        self.assertEqual(0, code)
        self.assertEqual("SOURCE_UNAVAILABLE", self.snapshot_status("testsrc"))


if __name__ == "__main__":
    unittest.main()
