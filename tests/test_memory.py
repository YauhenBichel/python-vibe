"""What a run remembers, and what it is allowed to forget.

Memory used to be a bare list that only grew. The harness sent no
context size, so Ollama applied its own default of 4096 tokens and threw
away the oldest messages once a run passed it. The oldest message is the
opening, which carries the file the harness located. The run lost the
part it had done work to assemble and said nothing about it.
"""

import unittest

from harness.memory import Conversation
from harness.model.ollama_generate import CONTEXT_TOKENS


class ConversationTest(unittest.TestCase):
    def _run(self, mem: Conversation, turns: int, opening: str) -> list[int]:
        sizes, prompt = [], opening
        for _ in range(turns):
            messages = mem.messages(prompt)
            sizes.append(sum(len(m["content"]) for m in messages))
            mem.remember(prompt, "reply " * 40)
            prompt = "tool result " * 40
        return sizes

    def test_it_stops_growing_at_the_budget(self) -> None:
        mem = Conversation(budget_tokens=2048, system="s" * 400)
        sizes = self._run(mem, 20, "x" * 5300)
        self.assertLessEqual(max(sizes), mem.budget_chars)
        self.assertEqual(sizes[-1], sizes[-2], "should be flat once trimming")

    def test_the_opening_survives_to_the_last_turn(self) -> None:
        """It carries the located file. Everything else is replaceable."""
        opening = "the located file " * 300
        mem = Conversation(budget_tokens=2048, system="s")
        self._run(mem, 20, opening)
        last = mem.messages("next")
        self.assertTrue(
            any(m["content"] == opening for m in last),
            "the opening was dropped, which is what used to happen",
        )

    def test_the_middle_is_what_goes(self) -> None:
        mem = Conversation(budget_tokens=1024, system="s")
        self._run(mem, 15, "x" * 2000)
        self.assertGreater(mem.dropped, 0)
        messages = mem.messages("next")
        self.assertEqual(messages[-1]["content"], "next", "the question stays")

    def test_a_short_run_keeps_everything(self) -> None:
        mem = Conversation(budget_tokens=8192, system="s")
        self._run(mem, 3, "small opening")
        self.assertEqual(mem.dropped, 0)

    def test_the_system_line_comes_first(self) -> None:
        mem = Conversation(budget_tokens=8192, system="be careful")
        messages = mem.messages("hello")
        self.assertEqual(messages[0], {"role": "system", "content": "be careful"})

    def test_an_opening_too_large_for_the_budget_is_dropped_not_cut(self) -> None:
        """Half a function read as a whole one is worse than none."""
        mem = Conversation(budget_tokens=64, system="s")
        mem.remember("x" * 10_000, "reply")
        messages = mem.messages("question")
        self.assertNotIn("x" * 10_000, [m["content"] for m in messages])
        self.assertEqual(messages[-1]["content"], "question")


class ContextSizeTest(unittest.TestCase):
    """Ollama's default is 4096 for weights that accept 131072."""

    def test_the_harness_states_a_size(self) -> None:
        self.assertGreaterEqual(CONTEXT_TOKENS, 8192)

    def test_the_request_carries_it(self) -> None:
        from pathlib import Path

        source = Path("src/harness/model/ollama_generate.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('"num_ctx"', source)

    def test_the_budget_matches_what_is_asked_for(self) -> None:
        """Trimming to more than the model will read defeats the point."""
        mem = Conversation(budget_tokens=CONTEXT_TOKENS)
        self.assertEqual(mem.budget_tokens, CONTEXT_TOKENS)


if __name__ == "__main__":
    unittest.main()
