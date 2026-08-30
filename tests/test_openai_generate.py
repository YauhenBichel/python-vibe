"""OpenAI-compatible generate. No live host, no token in assertions."""

import io
import json
import os
import unittest
from unittest import mock
from urllib.error import HTTPError

from harness.model.openai_generate import (
    HF_ROUTER,
    OpenAIGenerate,
    chat_url,
    resolve_openai_endpoint,
)


class ChatUrlTest(unittest.TestCase):
    def test_adds_the_chat_path(self) -> None:
        self.assertEqual(
            chat_url("https://example.test/v1"),
            "https://example.test/v1/chat/completions",
        )

    def test_keeps_a_full_path(self) -> None:
        full = "https://example.test/v1/chat/completions"
        self.assertEqual(chat_url(full), full)


class ResolveEndpointTest(unittest.TestCase):
    def test_missing_url_and_token_is_a_clear_error(self) -> None:
        env = {key: value for key, value in os.environ.items() if key not in {
            "PYTHON_VIBE_BASE_URL",
            "OPENAI_BASE_URL",
            "PYTHON_VIBE_API_KEY",
            "HF_TOKEN",
            "HUGGING_FACE_HUB_TOKEN",
            "OPENAI_API_KEY",
        }}
        with mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ValueError) as caught:
                resolve_openai_endpoint()
        self.assertIn("PYTHON_VIBE_BASE_URL", str(caught.exception))
        self.assertNotIn("sk-", str(caught.exception))

    def test_a_token_without_a_url_uses_the_hub_router(self) -> None:
        env = {
            "HF_TOKEN": "hf_not_a_real_token",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            base, key = resolve_openai_endpoint()
        self.assertEqual(base, HF_ROUTER)
        self.assertEqual(key, "hf_not_a_real_token")

    def test_an_explicit_url_wins(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            base, key = resolve_openai_endpoint(
                base_url="https://gpu.example/v1",
                api_key="secret-value-do-not-print",
            )
        self.assertEqual(base, "https://gpu.example/v1")
        self.assertEqual(key, "secret-value-do-not-print")


class OpenAIGenerateTest(unittest.TestCase):
    def test_reads_the_assistant_text(self) -> None:
        payload = json.dumps(
            {
                "choices": [
                    {"message": {"role": "assistant", "content": "Action: done"}}
                ]
            }
        ).encode("utf-8")
        resp = mock.Mock()
        resp.read.return_value = payload
        resp.__enter__ = lambda self: self
        resp.__exit__ = mock.Mock(return_value=False)
        with mock.patch(
            "harness.model.openai_generate.urllib.request.urlopen",
            return_value=resp,
        ) as opener:
            backend = OpenAIGenerate(
                "Qwen/Qwen2.5-Coder-32B-Instruct",
                "sys",
                base_url="https://gpu.example/v1",
                api_key="secret-value-do-not-print",
            )
            text = backend("hello")
        self.assertEqual(text, "Action: done")
        req = opener.call_args[0][0]
        self.assertEqual(
            req.full_url, "https://gpu.example/v1/chat/completions"
        )
        self.assertEqual(
            req.headers.get("Authorization")
            or req.get_header("Authorization"),
            "Bearer secret-value-do-not-print",
        )

    def test_http_errors_do_not_echo_the_key(self) -> None:
        err = HTTPError(
            "https://gpu.example/v1/chat/completions",
            401,
            "unauthorized",
            {},
            io.BytesIO(b""),
        )
        with mock.patch(
            "harness.model.openai_generate.urllib.request.urlopen",
            side_effect=err,
        ):
            backend = OpenAIGenerate(
                "demo",
                "sys",
                base_url="https://gpu.example/v1",
                api_key="secret-value-do-not-print",
            )
            with self.assertRaises(RuntimeError) as caught:
                backend("hello")
        self.assertIn("HTTP 401", str(caught.exception))
        self.assertNotIn("secret-value-do-not-print", str(caught.exception))



class SharedBackendTest(unittest.TestCase):
    """Both hosts post messages and read one reply. Only the edges differ.

    The two files were 64% the same lines: building the request, opening
    it, turning a failure into a message, pulling the text out. What a
    host actually has to say for itself is five things, and a new one
    should be those five rather than another copy of the transport.
    """

    def test_both_are_the_same_kind_of_thing(self) -> None:
        from harness.model.chat_backend import ChatBackend
        from harness.model.ollama_generate import OllamaGenerate
        from harness.model.openai_generate import OpenAIGenerate

        for kind in (OllamaGenerate, OpenAIGenerate):
            with self.subTest(backend=kind.__name__):
                self.assertTrue(issubclass(kind, ChatBackend))

    def test_each_says_where_to_post_and_what_to_send(self) -> None:
        from harness.model.ollama_generate import OllamaGenerate

        backend = OllamaGenerate("llama3.1:8b", "system")
        self.assertTrue(backend.url().endswith("/api/chat"))
        body = backend.body([{"role": "user", "content": "hello"}])
        self.assertEqual(body["model"], "llama3.1:8b")
        self.assertIn("num_ctx", body["options"])

    def test_each_knows_where_its_reply_sits(self) -> None:
        from harness.model.ollama_generate import OllamaGenerate
        from harness.model.openai_generate import OpenAIGenerate

        ollama = OllamaGenerate("m", "s")
        self.assertEqual(
            ollama.reply_from({"message": {"content": "hi"}}), "hi"
        )
        remote = OpenAIGenerate("m", "s", base_url="https://x/v1", api_key="k")
        self.assertEqual(
            remote.reply_from({"choices": [{"message": {"content": "hi"}}]}), "hi"
        )
        self.assertEqual(remote.reply_from({"choices": []}), "")

    def test_the_transport_lives_in_one_place(self) -> None:
        """Neither subclass should be opening its own connection."""
        from pathlib import Path

        root = Path(__file__).resolve().parents[1] / "src" / "harness" / "model"
        for name in ("ollama_generate.py", "openai_generate.py"):
            with self.subTest(module=name):
                source = (root / name).read_text(encoding="utf-8")
                self.assertNotIn("urlopen(request", source)


if __name__ == "__main__":
    unittest.main()
