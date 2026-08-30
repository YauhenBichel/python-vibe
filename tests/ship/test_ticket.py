import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from harness.ship.ticket import (
    identity_from_user_json,
    parse_ticket,
    render_ticket,
)
from harness.task import (
    issue_number,
    looks_like_pr_ref,
    looks_like_ship,
    looks_like_ticket,
    looks_like_ticket_work,
)


class TicketKindTest(unittest.TestCase):
    def test_fix_issue_is_work_not_only_ship(self) -> None:
        self.assertEqual(issue_number("fix issue #50"), "50")
        self.assertTrue(looks_like_ticket("fix #50"))
        self.assertTrue(looks_like_ticket_work("fix #50"))
        self.assertFalse(looks_like_ship("fix issue #50"))
        self.assertTrue(looks_like_ship("create a pr for #50"))
        self.assertTrue(looks_like_pr_ref("read pr 108"))
        self.assertFalse(looks_like_pr_ref("fix issue #50"))


class TicketBriefTest(unittest.TestCase):
    def test_names_file_job_and_next_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "orders.py").write_text("def apply_discount():\n    return 0\n")
            payload = json.dumps(
                {
                    "number": 96,
                    "title": "Write tests for apply_discount",
                    "body": (
                        "Cover `apply_discount` in src/orders.py\n\n"
                        "## Done when\n"
                        "- AAA tests exist\n"
                    ),
                    "state": "OPEN",
                    "comments": [
                        {
                            "author": {"login": "claude"},
                            "body": "Put the tests in tests/test_orders.py next to the others.",
                        },
                        {
                            "author": {"login": "someone"},
                            "body": "plus one",
                        },
                    ],
                }
            )
            ticket = parse_ticket(payload, root, viewer="YauhenBichel")
            self.assertIsNotNone(ticket)
            assert ticket is not None
            self.assertEqual(ticket.files, ("src/orders.py",))
            self.assertEqual(ticket.job, "write-tests")
            self.assertEqual(ticket.symbols, ("apply_discount",))
            self.assertTrue(ticket.todo)
            self.assertEqual(ticket.peers[0][0], "claude")
            shown = render_ticket(ticket)
            self.assertIn("viewing as @YauhenBichel", shown)
            self.assertIn("Where (files in this project)", shown)
            self.assertIn("src/orders.py", shown)
            self.assertIn("Job: write-tests", shown)
            self.assertIn("Also on this ticket:", shown)
            self.assertIn("@claude:", shown)
            self.assertIn("Next: Action: read Path: src/orders.py", shown)
            self.assertNotIn("@someone:", shown)

    def test_pr_files_from_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "orders.py").write_text("x = 1\n")
            payload = json.dumps(
                {
                    "number": 108,
                    "title": "Fix NameError",
                    "body": "The name is unbound.",
                    "state": "OPEN",
                    "files": [{"path": "src/orders.py"}],
                }
            )
            ticket = parse_ticket(payload, root, kind="pull request")
            self.assertIsNotNone(ticket)
            assert ticket is not None
            self.assertEqual(ticket.files, ("src/orders.py",))
            self.assertIn("Action: read Path: src/orders.py", render_ticket(ticket))

    def test_identity_from_user_json(self) -> None:
        login, name, email = identity_from_user_json(
            '{"login":"YauhenBichel","name":"Yauhen","email":""}'
        )
        self.assertEqual(login, "YauhenBichel")
        self.assertEqual(name, "Yauhen")
        self.assertEqual(email, "YauhenBichel@users.noreply.github.com")


if __name__ == "__main__":
    unittest.main()
