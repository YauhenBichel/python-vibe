import importlib.util
import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_serve():
    spec = importlib.util.spec_from_file_location(
        "python_vibe_serve", ROOT / "scripts" / "serve.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SERVE = _load_serve()


class ServeSidecarTest(unittest.TestCase):
    """/health probes Ollama before replying, so the client waits longer
    than that probe's own timeout."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), SERVE.Handler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        host, port = cls.httpd.server_address[:2]
        cls.base = f"http://{host}:{port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def _get(self, path: str):
        with urllib.request.urlopen(self.base + path, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))

    def _post(self, path: str, raw: bytes, content_type: str = "application/json"):
        req = urllib.request.Request(
            self.base + path,
            data=raw,
            headers={"Content-Type": content_type},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    def test_default_bind_is_localhost(self) -> None:
        self.assertEqual(SERVE.DEFAULT_HOST, "127.0.0.1")
        self.assertGreaterEqual(SERVE.MAX_BODY, 1024)

    def test_health(self) -> None:
        status, payload = self._get("/health")
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertIn("python-vibe", payload["models"])

    def test_unknown_route(self) -> None:
        status, payload = self._post("/v1/nope", b"{}")
        self.assertEqual(status, 404)
        self.assertEqual(payload["error"], "not found")

    def test_empty_prompt(self) -> None:
        status, payload = self._post("/v1/python-vibe", b'{"prompt":"  "}')
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"], "prompt required")

    def test_invalid_json(self) -> None:
        status, payload = self._post("/v1/python-vibe", b"not-json")
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"], "invalid json")

    def test_body_cap(self) -> None:
        raw = b'{"prompt":"' + (b"x" * (SERVE.MAX_BODY + 8)) + b'"}'
        status, payload = self._post("/v1/python-vibe", raw)
        self.assertEqual(status, 413)
        self.assertEqual(payload["error"], "body too large")


if __name__ == "__main__":
    unittest.main()
