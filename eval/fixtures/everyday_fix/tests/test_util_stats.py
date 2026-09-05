import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pkg.util_stats import compute_total


class TestUtilStats(unittest.TestCase):
    def test_compute_total(self) -> None:
        self.assertEqual(compute_total([1.0, 2.0, 3.0]), 6.0)


if __name__ == "__main__":
    unittest.main()
