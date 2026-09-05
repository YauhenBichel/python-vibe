"""Held-out execution tasks. None of these prompts are in the 45 train pairs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Task:
    id: str
    prompt: str
    reference: str
    argv: tuple[str, ...] = ()
    stdin: str = ""
    expect_stdout: str = ""
    files: tuple[tuple[str, str], ...] = ()
    timeout: float = 8.0


RUN_PREFIX = (
    "Reply with one fenced ```python block only. "
    "Call main() from `if __name__ == '__main__'` so running the file prints. "
    "Stdlib only. Read extra args from sys.argv. "
    "Print exactly what is asked — no extra text.\n\n"
)

REPAIR_PREFIX = (
    "The script failed when I ran it. Fix it.\n"
    "Reply with one complete fenced python block.\n"
)


def all_tasks() -> tuple[Task, ...]:
    return _TASKS


_TASKS: tuple[Task, ...] = (
    Task(
        id="weekday",
        prompt="Print the English weekday name for a YYYY-MM-DD date in sys.argv[1].",
        argv=("2026-08-29",),
        expect_stdout="Saturday\n",
        reference="""
import sys
from datetime import date

def main() -> None:
    y, m, d = sys.argv[1].split("-")
    print(date(int(y), int(m), int(d)).strftime("%A"))

if __name__ == "__main__":
    main()
""",
    ),
    Task(
        id="count-ext",
        prompt=(
            "Count files in directory sys.argv[1] whose names end with sys.argv[2] "
            "(example: .md). Do not recurse. Print the integer count."
        ),
        argv=(".", ".md"),
        files=(("a.md", "x"), ("b.md", "y"), ("c.txt", "z"), ("notes.md.bak", "q")),
        expect_stdout="2\n",
        reference="""
import sys
from pathlib import Path

def main() -> None:
    root = Path(sys.argv[1])
    suffix = sys.argv[2]
    print(sum(1 for p in root.iterdir() if p.is_file() and p.name.endswith(suffix)))

if __name__ == "__main__":
    main()
""",
    ),
    Task(
        id="fizzbuzz",
        prompt=(
            "Print FizzBuzz for 1..N inclusive, N from sys.argv[1]. "
            "Fizz on multiples of 3, Buzz on 5, FizzBuzz on both. One value per line."
        ),
        argv=("15",),
        expect_stdout=(
            "1\n2\nFizz\n4\nBuzz\nFizz\n7\n8\nFizz\nBuzz\n11\nFizz\n13\n14\nFizzBuzz\n"
        ),
        reference="""
import sys

def main() -> None:
    n = int(sys.argv[1])
    for i in range(1, n + 1):
        out = ""
        if i % 3 == 0:
            out += "Fizz"
        if i % 5 == 0:
            out += "Buzz"
        print(out or i)

if __name__ == "__main__":
    main()
""",
    ),
    Task(
        id="clamp",
        prompt="Print clamp(x, lo, hi) for three integers sys.argv[1:4] (x, lo, hi).",
        argv=("12", "0", "10"),
        expect_stdout="10\n",
        reference="""
import sys

def main() -> None:
    x, lo, hi = (int(a) for a in sys.argv[1:4])
    print(min(hi, max(lo, x)))

if __name__ == "__main__":
    main()
""",
    ),
    Task(
        id="slugify",
        prompt=(
            "Slugify sys.argv[1]: lowercase, replace each run of non-ascii-letters/"
            "digits with one hyphen, strip leading/trailing hyphens. Print the slug."
        ),
        argv=("Hello, World!",),
        expect_stdout="hello-world\n",
        reference="""
import re
import sys

def main() -> None:
    text = re.sub(r"[^a-z0-9]+", "-", sys.argv[1].lower()).strip("-")
    print(text)

if __name__ == "__main__":
    main()
""",
    ),
    Task(
        id="median",
        prompt="Print the median of the integers in sys.argv[1:]. For even n, print the lower middle (integer).",
        argv=("1", "3", "2", "9", "5"),
        expect_stdout="3\n",
        reference="""
import sys

def main() -> None:
    nums = sorted(int(a) for a in sys.argv[1:])
    print(nums[(len(nums) - 1) // 2])

if __name__ == "__main__":
    main()
""",
    ),
    Task(
        id="hhmmss",
        prompt="Convert a non-negative integer number of seconds (sys.argv[1]) to HH:MM:SS with zero-padded fields.",
        argv=("3661",),
        expect_stdout="01:01:01\n",
        reference="""
import sys

def main() -> None:
    total = int(sys.argv[1])
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    print(f"{h:02d}:{m:02d}:{s:02d}")

if __name__ == "__main__":
    main()
""",
    ),
    Task(
        id="rotate",
        prompt=(
            "Left-rotate the words in sys.argv[2:] by k=int(sys.argv[1]) positions. "
            "Print the words joined by a single space."
        ),
        argv=("2", "a", "b", "c", "d"),
        expect_stdout="c d a b\n",
        reference="""
import sys

def main() -> None:
    k = int(sys.argv[1])
    words = sys.argv[2:]
    k %= len(words)
    print(" ".join(words[k:] + words[:k]))

if __name__ == "__main__":
    main()
""",
    ),
    Task(
        id="unique-order",
        prompt="Print the words in sys.argv[1:] with duplicates removed, first occurrence kept, space-separated.",
        argv=("a", "b", "a", "c", "b"),
        expect_stdout="a b c\n",
        reference="""
import sys

def main() -> None:
    seen: list[str] = []
    for word in sys.argv[1:]:
        if word not in seen:
            seen.append(word)
    print(" ".join(seen))

if __name__ == "__main__":
    main()
""",
    ),
    Task(
        id="palindrome",
        prompt=(
            "Print yes or no: is sys.argv[1] a palindrome if you lowercase it and "
            "drop every character that is not a-z or 0-9?"
        ),
        argv=("RaceCar",),
        expect_stdout="yes\n",
        reference="""
import sys

def main() -> None:
    chars = [c for c in sys.argv[1].lower() if c.isalnum() and c.isascii()]
    print("yes" if chars == chars[::-1] else "no")

if __name__ == "__main__":
    main()
""",
    ),
    Task(
        id="fib",
        prompt="Print F(n) where F(0)=0, F(1)=1, n=int(sys.argv[1]).",
        argv=("10",),
        expect_stdout="55\n",
        reference="""
import sys

def main() -> None:
    n = int(sys.argv[1])
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    print(a)

if __name__ == "__main__":
    main()
""",
    ),
    Task(
        id="sum-even",
        prompt="Print the sum of the even integers in sys.argv[1:].",
        argv=("1", "2", "3", "4", "5", "6"),
        expect_stdout="12\n",
        reference="""
import sys

def main() -> None:
    print(sum(int(a) for a in sys.argv[1:] if int(a) % 2 == 0))

if __name__ == "__main__":
    main()
""",
    ),
    Task(
        id="csv-col",
        prompt=(
            "Read CSV from stdin (no quotes). Print 0-based column sys.argv[1], "
            "one cell per line."
        ),
        argv=("1",),
        stdin="a,1\nb,2\n",
        expect_stdout="1\n2\n",
        reference="""
import sys

def main() -> None:
    idx = int(sys.argv[1])
    for line in sys.stdin:
        line = line.rstrip("\\n")
        if not line:
            continue
        print(line.split(",")[idx])

if __name__ == "__main__":
    main()
""",
    ),
    Task(
        id="indent4",
        prompt="Read stdin and print it again with four spaces prepended to every line. Keep the last newline.",
        stdin="foo\nbar\n",
        expect_stdout="    foo\n    bar\n",
        reference="""
import sys

def main() -> None:
    for line in sys.stdin:
        if line.endswith("\\n"):
            print("    " + line[:-1])
        else:
            print("    " + line, end="")

if __name__ == "__main__":
    main()
""",
    ),
    Task(
        id="anagram",
        prompt=(
            "Print yes or no: are sys.argv[1] and sys.argv[2] anagrams after "
            "lowercasing and dropping spaces?"
        ),
        argv=("listen", "silent"),
        expect_stdout="yes\n",
        reference="""
import sys

def norm(text: str) -> list[str]:
    return sorted(c for c in text.lower() if c != " ")

def main() -> None:
    print("yes" if norm(sys.argv[1]) == norm(sys.argv[2]) else "no")

if __name__ == "__main__":
    main()
""",
    ),
    Task(
        id="wrap",
        prompt=(
            "Word-wrap stdin to width N=int(sys.argv[1]). Split on spaces. "
            "If a word is longer than N, put it on its own line. Print one wrapped line per row."
        ),
        argv=("5",),
        stdin="hello world\n",
        expect_stdout="hello\nworld\n",
        reference="""
import sys

def main() -> None:
    width = int(sys.argv[1])
    words = sys.stdin.read().split()
    line: list[str] = []
    size = 0
    for word in words:
        extra = len(word) if not line else len(word) + 1
        if line and size + extra > width:
            print(" ".join(line))
            line = [word]
            size = len(word)
        else:
            line.append(word)
            size += extra
    if line:
        print(" ".join(line))

if __name__ == "__main__":
    main()
""",
    ),
    Task(
        id="iso-date",
        prompt="Print YYYY-MM-DD from an ISO-8601 timestamp in sys.argv[1] (may include time and timezone).",
        argv=("2026-09-05T17:27:00",),
        expect_stdout="2026-09-05\n",
        reference="""
import sys
from datetime import datetime

def main() -> None:
    raw = sys.argv[1]
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    print(datetime.fromisoformat(raw).date().isoformat())

if __name__ == "__main__":
    main()
""",
    ),
    Task(
        id="relpath",
        prompt="Print path sys.argv[2] relative to directory sys.argv[1], using forward slashes.",
        argv=("/Users/x/proj", "/Users/x/proj/src/a.py"),
        expect_stdout="src/a.py\n",
        reference="""
import sys
from pathlib import Path

def main() -> None:
    print(Path(sys.argv[2]).relative_to(sys.argv[1]).as_posix())

if __name__ == "__main__":
    main()
""",
    ),
)
