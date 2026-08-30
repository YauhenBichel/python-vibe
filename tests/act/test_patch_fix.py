import unittest

from harness.act.patch_fix import align_indent, find_match, miss_message, suggestions

FILE = """import unittest


class AppTest(unittest.TestCase):
    def test_total(self) -> None:
        self.assertEqual(compute_total([1, 2]), 3)
"""


class FindMatchTest(unittest.TestCase):
    def test_exact_unique_match_stays_exact(self) -> None:
        match = find_match(FILE, "        self.assertEqual(compute_total([1, 2]), 3)")
        self.assertIsNotNone(match)
        self.assertTrue(match.exact)

    def test_respaced_line_still_matches(self) -> None:
        match = find_match(FILE, "def  test_total(self)  -> None:")
        self.assertIsNotNone(match)
        self.assertFalse(match.exact)
        self.assertEqual(match.text, "    def test_total(self) -> None:")

    def test_ambiguous_normalised_match_is_refused(self) -> None:
        text = "    x = 1\n    y = 2\nx = 1\n"
        self.assertIsNone(find_match(text, "x = 1"))

    def test_absent_string_is_no_match(self) -> None:
        self.assertIsNone(find_match(FILE, "def nothing_like_this():"))

    def test_multi_line_find_normalises(self) -> None:
        match = find_match(FILE, "def test_total(self) -> None:\nself.assertEqual(compute_total([1, 2]), 3)")
        self.assertIsNotNone(match)
        self.assertFalse(match.exact)


class SuggestionTest(unittest.TestCase):
    def test_near_miss_names_the_real_line(self) -> None:
        close = suggestions(FILE, "self.assertEqual(compute_total([1,2]), 4)")
        self.assertTrue(any("compute_total" in item for item in close))

    def test_message_tells_the_model_what_to_do(self) -> None:
        self.assertIn("copy one whole line", miss_message(FILE, "self.assertEqual(compute_total([9]), 9)"))

    def test_message_without_any_close_line(self) -> None:
        self.assertIn("Find: string not in file", miss_message(FILE, "zzzzzzzzzzzz"))


class AlignIndentTest(unittest.TestCase):
    def test_replace_inherits_the_matched_indent(self) -> None:
        out = align_indent("        return total", "return sum(rows)")
        self.assertEqual(out, "        return sum(rows)")

    def test_replace_that_already_has_indent_is_untouched(self) -> None:
        self.assertEqual(align_indent("        a", "    b"), "    b")

    def test_top_level_match_is_untouched(self) -> None:
        self.assertEqual(align_indent("def f():", "def g():"), "def g():")


if __name__ == "__main__":
    unittest.main()
