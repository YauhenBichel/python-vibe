import unittest

from src.orders import compute_total, apply_discount


class TestComputeTotal(unittest.TestCase):
    def test_compute_total_sums_the_line_prices(self) -> None:
        prices = [10, 20, 30]
        got = compute_total(prices)
        self.assertEqual(got, 60)

    def test_apply_discount_returns_the_expected_result(self) -> None:
        total, percent = 100, 10
        got = apply_discount(total, percent)
        self.assertEqual(got, 90)


if __name__ == "__main__":
    unittest.main()
