import unittest

from src.app import add


class AppTest(unittest.TestCase):
    def test_add_returns_the_sum(self) -> None:
        self.assertEqual(add(2, 3), 5)
