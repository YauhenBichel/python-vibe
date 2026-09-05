import unittest

from src.app import compute_total


class AppTest(unittest.TestCase):
    def test_compute_total_sums_the_rows(self) -> None:
        self.assertEqual(compute_total([1, 2]), 3)
