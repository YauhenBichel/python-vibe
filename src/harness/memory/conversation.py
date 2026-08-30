"""What a run remembers between turns, and what it is allowed to forget.

Memory used to be a bare list on the generate function. Every turn
appended the prompt and the reply, nothing was ever removed, and the
request grew about 130 tokens a turn on top of an opening that is
usually over a thousand.

Nobody decided where that stopped. The harness sent no context size, so
Ollama applied its own default — 4096 tokens for a model whose weights
accept 131072 — and when a run crossed it the oldest messages were
dropped by the server. The oldest message is the opening: the file the
harness located and the instruction saying what to do with it. The run
lost exactly the part it had done work to assemble, and said nothing.

This decides instead. The opening is kept whatever else goes, because it
is the only turn that carries the code. Recent turns are kept because
that is where the run is. What goes is the middle, which is where a
model has already been told it used the wrong verb four times.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Roughly four characters to a token. Only used to decide what to drop,
# so it does not need to match a tokeniser.
CHARS_PER_TOKEN = 4


@dataclass
class Conversation:
    """The messages one run sends, and the budget they have to fit.

    Fields:
        budget_tokens: how much the model will read. Everything above
            this is dropped here, in the open, rather than by the server.
        system: the instruction that opens every request.
        opening: the first prompt, which carries the located file. Kept
            for as long as the run lasts.
        turns: prompt and reply for every turn after the first.
        dropped: how many middle turns have been let go, so a caller can
            say so rather than guess.
    """

    budget_tokens: int = 8192
    system: str = ""
    opening: str = ""
    turns: list[tuple[str, str]] = field(default_factory=list)
    dropped: int = 0

    @property
    def budget_chars(self) -> int:
        return self.budget_tokens * CHARS_PER_TOKEN

    def remember(self, prompt: str, reply: str) -> None:
        """Record one exchange. The first prompt becomes the opening."""
        if not self.opening:
            self.opening = prompt
            self.turns.append(("", reply))
            return
        self.turns.append((prompt, reply))

    def messages(self, prompt: str) -> list[dict[str, str]]:
        """What to send for `prompt`, trimmed from the middle to fit."""
        head: list[dict[str, str]] = []
        if self.system:
            head.append({"role": "system", "content": self.system})
        if self.opening:
            head.append({"role": "user", "content": self.opening})

        body: list[dict[str, str]] = []
        for asked, answered in self.turns:
            if asked:
                body.append({"role": "user", "content": asked})
            if answered:
                body.append({"role": "assistant", "content": answered})
        tail = [{"role": "user", "content": prompt}]

        fixed = _size(head) + _size(tail)
        room = self.budget_chars - fixed
        if room <= 0:
            # Even the opening does not fit. Send the instruction and the
            # question: a truncated file is worse than none, because the
            # model reads half a function and answers about it.
            self.dropped = len(self.turns)
            return ([head[0]] if self.system else []) + tail

        kept: list[dict[str, str]] = []
        for message in reversed(body):
            if _size(kept) + len(message["content"]) > room:
                break
            kept.insert(0, message)
        self.dropped = max(0, (len(body) - len(kept) + 1) // 2)
        return head + kept + tail


def _size(messages: list[dict[str, str]]) -> int:
    return sum(len(message["content"]) for message in messages)
