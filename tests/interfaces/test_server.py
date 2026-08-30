"""The HTTP surface. No model: only routing, refusals and shapes."""

import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from harness.server import HOST, make_handler


def _project(tmp: str) -> Path:
    root = Path(tmp)
    (root / "app.py").write_text("def go() -> int:\n    return 1\n", encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "test_app.py").write_text("x = 1\n", encoding="utf-8")
    return root


class ServerTest(unittest.TestCase):
    def _serve(self, project: Path, *, allow_writes: bool):
        handler = make_handler(project, allow_writes=allow_writes, model="none")
        httpd = ThreadingHTTPServer((HOST, 0), handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        # addCleanup runs last-registered first, so register server_close
        # first and shutdown second. Closing the socket while serve_forever
        # is still running yanks it from under in-flight handlers, which
        # Windows reports as WinError 10038.
        self.addCleanup(httpd.server_close)
        self.addCleanup(httpd.shutdown)
        return f"http://{HOST}:{httpd.server_address[1]}"

    def _post(self, base: str, path: str, payload: dict):
        request = urllib.request.Request(
            base + path,
            data=json.dumps(payload).encode(),
            headers={"content-type": "application/json", "connection": "close"},
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def test_binds_loopback_only(self) -> None:
        self.assertEqual(HOST, "127.0.0.1")

    def test_health_reports_the_write_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = self._serve(_project(tmp), allow_writes=False)
            with urllib.request.urlopen(base + "/health", timeout=20) as response:
                body = json.loads(response.read())
        self.assertFalse(body["allow_writes"])
        self.assertNotIn("/v1/run", body["routes"])

    def test_run_is_refused_when_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = self._serve(_project(tmp), allow_writes=False)
            status, body = self._post(base, "/v1/run", {"task": "add a function"})
        self.assertEqual(status, 403)
        self.assertIn("read-only", body["error"])

    def test_layout_needs_no_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = self._serve(_project(tmp), allow_writes=False)
            status, body = self._post(base, "/v1/layout", {})
        self.assertEqual(status, 200)
        self.assertIn("layout", body)

    def test_brief_needs_no_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = self._serve(_project(tmp), allow_writes=False)
            status, body = self._post(base, "/v1/brief", {})
        self.assertEqual(status, 200)
        self.assertIn("Mode:", body["brief"])

    def test_unknown_route_is_404(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = self._serve(_project(tmp), allow_writes=False)
            status, _body = self._post(base, "/v1/nope", {})
        self.assertEqual(status, 404)

    def test_task_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = self._serve(_project(tmp), allow_writes=False)
            status, body = self._post(base, "/v1/ask", {})
        self.assertEqual(status, 400)
        self.assertIn("task", body["error"])

    def test_models_needs_no_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = self._serve(_project(tmp), allow_writes=False)
            with urllib.request.urlopen(base + "/v1/models", timeout=20) as response:
                body = json.loads(response.read())
        self.assertEqual(body["object"], "list")
        self.assertTrue(body["data"])

    def test_chat_write_is_refused_when_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = self._serve(_project(tmp), allow_writes=False)
            status, body = self._post(
                base,
                "/v1/chat/completions",
                {
                    "model": "none",
                    "messages": [
                        {"role": "user", "content": "add a function multiply"}
                    ],
                },
            )
        self.assertEqual(status, 403)
        self.assertIn("read-only", body["error"])

    def test_chat_stream_is_400(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = self._serve(_project(tmp), allow_writes=False)
            status, body = self._post(
                base,
                "/v1/chat/completions",
                {
                    "model": "none",
                    "stream": True,
                    "messages": [{"role": "user", "content": "what does go return?"}],
                },
            )
        self.assertEqual(status, 400)
        self.assertIn("stream", body["error"])

    def test_invalid_json_is_400(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = self._serve(_project(tmp), allow_writes=False)
            request = urllib.request.Request(
                base + "/v1/ask", data=b"{not json",
                headers={"content-type": "application/json"},
            )
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    status = response.status
            except urllib.error.HTTPError as exc:
                status = exc.code
        self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
