import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from harness.act.parse import parse_turn
from harness.task import everyday_example_path, looks_like_add_feature
from harness.skillkit.catalog import get_skill, list_skills, pick_skills, render_catalog, render_skill, skill_from_action

ROOT = Path(__file__).resolve().parents[1]


class SkillsTest(unittest.TestCase):
    def test_kit_lists_add_feature(self) -> None:
        catalog = list_skills(ROOT)
        names = {item.name for item in catalog}
        # A subset, not an exact set: adding a kit skill must not fail here.
        core = {
            "add-feature",
            "answer-question",
            "readable-layout",
            "stay-scoped",
            "write-tests",
        }
        self.assertEqual(core - names, set(), "kit is missing a core skill")
        loaded = get_skill("add-feature", ROOT)
        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertIn("Append:", loaded.body)

    def test_pick_on_add_task_not_on_question(self) -> None:
        catalog = list_skills(ROOT)
        self.assertTrue(looks_like_add_feature("add a function multiply and a test"))
        self.assertFalse(looks_like_add_feature("what does add return?"))
        self.assertFalse(looks_like_add_feature("create a package for total_price"))
        self.assertFalse(looks_like_add_feature("rename calc to total_price"))
        picked = pick_skills("add a function multiply(a, b) and a unit test", catalog)
        self.assertEqual([item.name for item in picked], ["add-feature", "write-tests"])
        self.assertEqual(
            [item.name for item in pick_skills("what does add return?", catalog)],
            ["answer-question"],
        )
        self.assertEqual(
            [item.name for item in pick_skills("create a package for total_price", catalog)],
            ["new-package"],
        )
        self.assertEqual(
            [
                item.name
                for item in pick_skills(
                    "rename calc to total_price to fix the code smell", catalog
                )
            ],
            ["fix-smell"],
        )
        self.assertEqual(
            [item.name for item in pick_skills("fix #50", catalog)],
            ["read-issue"],
        )
        self.assertEqual(
            [item.name for item in pick_skills("read pr 108", catalog)],
            ["read-issue"],
        )
        self.assertEqual(
            [item.name for item in pick_skills("create a pr for #50", catalog)],
            ["open-pr"],
        )
        self.assertEqual(
            [item.name for item in pick_skills("merge pr 16", catalog)],
            ["merge-pr"],
        )

    def test_render_and_parse_skill_action(self) -> None:
        catalog = list_skills(ROOT)
        text = render_catalog(catalog)
        self.assertIn("add-feature", text)
        skill = get_skill("write-tests", ROOT)
        assert skill is not None
        self.assertIn("unittest", render_skill(skill))
        turn = parse_turn("Action: skill\nName: add-feature")
        self.assertIsNotNone(turn)
        assert turn is not None
        self.assertEqual(turn.action, "skill")
        self.assertEqual(turn.name, "add-feature")

    def test_everyday_paths_match_the_skill_files(self) -> None:
        for task, name in (
            ("write a weekday script from argv", "write-script"),
            ("fetch json from the HTTP API", "call-http"),
            ("tally counts by key from a csv", "analyze-data"),
            ("implement binary search", "write-algorithm"),
            ("write a pathlib helper for the venv", "write-paths"),
            ("add a CI workflow that runs the unit tests", "write-workflow"),
        ):
            skill = get_skill(name, ROOT)
            assert skill is not None
            path_line = next(
                line.split(":", 1)[1].strip()
                for line in skill.body.splitlines()
                if line.startswith("Path:")
            )
            self.assertEqual(everyday_example_path(task), path_line)

    def test_action_write_tests_is_a_skill(self) -> None:
        shortcut = skill_from_action("write-tests", project=ROOT)
        self.assertIsNotNone(shortcut)
        assert shortcut is not None
        self.assertEqual(shortcut.name, "write-tests")
        self.assertIsNone(skill_from_action("grep", project=ROOT))
        named = skill_from_action("skill", name="add-feature", project=ROOT)
        self.assertIsNotNone(named)
        assert named is not None
        self.assertEqual(named.name, "add-feature")

    def test_write_tests_skill_includes_aaa_fixture(self) -> None:
        skill = get_skill("write-tests", ROOT)
        self.assertIsNotNone(skill)
        assert skill is not None
        self.assertIn("test_weekday_returns_day_name", skill.body)
        self.assertIn("got = weekday(day_index)", skill.body)
        self.assertIn("self.assertEqual(got, \"Tuesday\")", skill.body)


if __name__ == "__main__":
    unittest.main()
