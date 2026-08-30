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



class NothingLeavesUnreadTest(unittest.TestCase):
    """The guard read drafts arriving and never the prompt going out.

    A run pointed at a remote host posted whatever the harness had
    gathered — for a named-file task, the whole file — with no check at
    all. These are the checks it has now.
    """

    def _sent(self, base: str = "https://example.test/v1"):
        return OpenAIGenerate(
            "org/model", "sys", base_url=base, api_key="unused-in-assertions"
        )

    def test_a_secret_in_the_prompt_stops_the_send(self) -> None:
        from harness.model.outbound import refuse_to_send

        leaked = [{"role": "user", "content": "key = 'AKIA" + "A" * 16 + "'"}]
        blocked = refuse_to_send(leaked, "https://example.test/v1")
        self.assertIn("an AWS access key", blocked)
        self.assertNotIn("AKIA", blocked)

    def test_the_refusal_never_quotes_what_it_found(self) -> None:
        """Printing the key to explain that it leaked would be the leak."""
        from harness.model.outbound import refuse_to_send

        token = "ghp_" + "b" * 24
        blocked = refuse_to_send(
            [{"role": "user", "content": token}], "https://example.test/v1"
        )
        self.assertIn("a GitHub token", blocked)
        self.assertNotIn(token, blocked)

    def test_a_local_host_is_not_a_send(self) -> None:
        from harness.model.outbound import leaves_this_machine, refuse_to_send

        self.assertFalse(leaves_this_machine("http://127.0.0.1:11434"))
        self.assertFalse(leaves_this_machine("http://localhost:8080/v1"))
        self.assertTrue(leaves_this_machine("https://router.huggingface.co/v1"))
        leaked = [{"role": "user", "content": "AKIA" + "C" * 16}]
        self.assertEqual(refuse_to_send(leaked, "http://127.0.0.1:11434"), "")

    def test_a_whole_repository_is_a_mistake_not_a_task(self) -> None:
        from harness.model.outbound import DEFAULT_MAX_CHARS, refuse_to_send

        huge = [{"role": "user", "content": "x" * (DEFAULT_MAX_CHARS + 1)}]
        blocked = refuse_to_send(huge, "https://example.test/v1")
        self.assertIn("Refusing to send", blocked)
        self.assertIn("PYTHON_VIBE_MAX_SEND", blocked)

    def test_the_cap_can_be_raised_by_someone_who_means_it(self) -> None:
        from harness.model.outbound import DEFAULT_MAX_CHARS, refuse_to_send

        huge = [{"role": "user", "content": "x" * (DEFAULT_MAX_CHARS + 1)}]
        with mock.patch.dict(
            os.environ, {"PYTHON_VIBE_MAX_SEND": str(DEFAULT_MAX_CHARS * 4)}
        ):
            self.assertEqual(refuse_to_send(huge, "https://example.test/v1"), "")

    def test_the_send_itself_is_stopped_not_just_reported(self) -> None:
        backend = self._sent()
        leaked = [{"role": "user", "content": "AKIA" + "D" * 16}]
        with mock.patch("urllib.request.urlopen") as opened:
            with self.assertRaises(RuntimeError) as caught:
                backend.send(leaked)
        opened.assert_not_called()
        self.assertIn("an AWS access key", str(caught.exception))

    def test_what_went_is_a_size_and_a_host_not_the_prompt(self) -> None:
        from harness.model.outbound import what_was_sent

        line = what_was_sent(
            [{"role": "user", "content": "private business logic"}],
            "https://example.test/v1",
        )
        self.assertIn("example.test", line)
        self.assertIn("22 characters", line)
        self.assertNotIn("private business logic", line)

    def test_a_run_says_once_that_something_left(self) -> None:
        backend = self._sent()
        answer = io.BytesIO(
            json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode()
        )
        answer.__enter__ = lambda s=answer: s  # type: ignore[attr-defined]
        answer.__exit__ = lambda *a: None  # type: ignore[attr-defined]
        said = io.StringIO()
        with mock.patch("sys.stderr", said):
            with mock.patch("urllib.request.urlopen", return_value=answer):
                backend.send([{"role": "user", "content": "hello"}])
        self.assertIn("sent 5 characters", said.getvalue())
        self.assertIn("example.test", said.getvalue())



class OneHomeForTheShapesTest(unittest.TestCase):
    """A shape learned once should be known everywhere.

    The same four patterns were written out in the guard and again in
    the trace redactor. Adding a third copy for the outbound check would
    have made a shape learned in one place unknown in two others.
    """

    def test_no_module_writes_the_shapes_out_again(self) -> None:
        import pathlib

        root = pathlib.Path(__file__).resolve().parents[1] / "src" / "harness"
        copies = sorted(
            str(p.relative_to(root))
            for p in root.rglob("*.py")
            if "ghp_" in p.read_text(encoding="utf-8")
        )
        self.assertEqual(copies, ["secrets.py"], f"a second copy in {copies}")

    def test_the_trace_still_redacts_what_it_used_to(self) -> None:
        """Consolidating must not narrow what a written-down trace hides."""
        from harness.observe.trace_record import redact

        for leak in ("ghp_" + "z" * 24, "AKIA" + "Y" * 16, "HF_TOKEN=abc",
                     "-----BEGIN RSA PRIVATE KEY-----"):
            self.assertEqual(redact(leak), "[redacted]", leak[:12])


if __name__ == "__main__":
    unittest.main()
