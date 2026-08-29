"""The co-author trailer python-vibe writes, and whether GitHub will link it.

The account has to be created by a person at github.com/signup. What the
code can do is write the trailer, take the real address once it exists,
and be honest about whether that address links.
"""

import os
import unittest
from unittest import mock

from harness.ship.identity import (
    COAUTHOR_ENV,
    co_author_email,
    co_author_line,
    co_author_links,
    with_co_author,
)


class TrailerTest(unittest.TestCase):
    def test_the_trailer_names_python_vibe(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(COAUTHOR_ENV, None)
            self.assertTrue(co_author_line().startswith("Co-authored-by:"))
            self.assertIn("python-vibe", co_author_line())

    def test_it_is_added_once_only(self) -> None:
        once = with_co_author("add a helper")
        twice = with_co_author(once)
        self.assertEqual(once.lower().count("co-authored-by"), 1)
        self.assertEqual(twice.lower().count("co-authored-by"), 1)

    def test_a_real_account_address_is_used_when_given(self) -> None:
        identity = "python-vibe <1234567+python-vibe@users.noreply.github.com>"
        with mock.patch.dict(os.environ, {COAUTHOR_ENV: identity}):
            self.assertIn("1234567+python-vibe", co_author_line())


class LinkingTest(unittest.TestCase):
    """A trailer that does not link records the work but shows no account."""

    def test_the_placeholder_does_not_link(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(COAUTHOR_ENV, None)
            self.assertFalse(co_author_links())

    def test_a_numbered_noreply_address_links(self) -> None:
        identity = "python-vibe <1234567+python-vibe@users.noreply.github.com>"
        with mock.patch.dict(os.environ, {COAUTHOR_ENV: identity}):
            self.assertTrue(co_author_links())
            self.assertEqual(
                co_author_email(), "1234567+python-vibe@users.noreply.github.com"
            )

    def test_an_ordinary_address_links(self) -> None:
        with mock.patch.dict(os.environ, {COAUTHOR_ENV: "python-vibe <bot@example.com>"}):
            self.assertTrue(co_author_links())

    def test_something_that_is_not_an_address_does_not(self) -> None:
        with mock.patch.dict(os.environ, {COAUTHOR_ENV: "python-vibe <not-an-address>"}):
            self.assertFalse(co_author_links())


if __name__ == "__main__":
    unittest.main()
