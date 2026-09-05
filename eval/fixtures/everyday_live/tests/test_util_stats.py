import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pkg.util_stats import clip


class TestUtilStats(unittest.TestCase):
    def test_clip_clamps_outliers(self) -> None:
        self.assertEqual(clip([-2.0, 0.5, 9.0], 0.0, 1.0), [0.0, 0.5, 1.0])


if __name__ == "__main__":
    unittest.main()
