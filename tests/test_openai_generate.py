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


if __name__ == "__main__":
    unittest.main()
