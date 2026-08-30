---
name: write-tests
description: Adds one AAA unittest that names the behavior. Use when adding a feature or when the user asks for tests.
---

One unittest.TestCase method. Name `test_<unit>_<result>`. Arrange inputs, Act into `got`, Assert `got`.
Do not write `test_multiply` or `assertEqual(multiply(2, 3), 6)` on one line.
Do not write a Find:.

Action: patch
Path: {{test}}
Append:
    def test_multiply_returns_the_product(self) -> None:
        left, right = 2, 3
        got = multiply(left, right)
        self.assertEqual(got, 6)

    def test_weekday_returns_day_name(self) -> None:
        day_index = 2
        got = weekday(day_index)
        self.assertEqual(got, "Tuesday")
