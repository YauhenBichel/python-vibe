import unittest

from harness.model.route import EVERYDAY, model_lane, route_advice, suggest_ollama


class ModelRouteTest(unittest.TestCase):
    def test_ship_needs_no_model(self) -> None:
        self.assertEqual(model_lane("create a pr for #50"), "none")
        self.assertEqual(suggest_ollama("merge pr 16"), "")

    def test_questions_stay_on_the_everyday_8b(self) -> None:
        self.assertEqual(model_lane("what does compute_total return?"), "read")
        self.assertEqual(suggest_ollama("what does compute_total return?"), EVERYDAY)

    def test_writes_stay_on_the_everyday_8b(self) -> None:
        self.assertEqual(model_lane("add a function multiply(a, b) and a test"), "write")
        self.assertEqual(
            model_lane("write tests for apply_discount in src/orders.py"), "write"
        )
        self.assertEqual(model_lane("rename calc to multiply"), "write")
        self.assertEqual(suggest_ollama("fix the NameError in src/orders.py"), EVERYDAY)

    def test_structure_review_is_its_own_lane(self) -> None:
        self.assertEqual(model_lane("review the project structure and refactor"), "structure")
        self.assertEqual(model_lane("review src/orders.py for bugs"), "read")

    def test_advice_never_names_tiny_as_the_pick(self) -> None:
        text = route_advice("add multiply(a, b)")
        self.assertIn(EVERYDAY, text)
        self.assertIn("Lane: write", text)
        self.assertNotIn("Use qwen2.5-coder:0.5b", text)


if __name__ == "__main__":
    unittest.main()
