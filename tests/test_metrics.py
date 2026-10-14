"""KPI定義の検証（python -m unittest）。"""
import unittest

import pandas as pd

from salon_kpi.metrics import compute, new_return_flags


def visits(rows):
    df = pd.DataFrame(rows, columns=["date", "store", "staff", "customer_key", "is_new", "is_nominated", "has_spa", "sales"])
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.strftime("%Y-%m")
    return df


EMPTY_COSTS = pd.DataFrame(columns=["month", "store", "labor_cost", "hpb_cost"])
EMPTY_PAY = pd.DataFrame(columns=["month", "store", "airpay_sales"])


class NewReturnRate(unittest.TestCase):
    def test_return_within_window_counts_and_outside_does_not(self):
        v = visits([
            ("2026-01-10", "s", "A", "c1", True, False, False, 10000),
            ("2026-03-01", "s", "A", "c1", False, True, False, 10000),   # 50日後 → 再来
            ("2026-01-20", "s", "A", "c2", True, False, False, 10000),
            ("2026-05-01", "s", "A", "c2", False, True, False, 10000),   # 101日後 → 対象外
            ("2026-06-30", "s", "B", "c3", False, False, False, 10000),
        ])
        f = new_return_flags(v, 90).set_index("customer_key")
        self.assertTrue(f.loc["c1", "returned"])
        self.assertFalse(f.loc["c2", "returned"])

    def test_immature_cohort_is_blank(self):
        v = visits([
            ("2026-01-10", "s", "A", "c1", True, False, False, 10000),
            ("2026-02-01", "s", "A", "c2", True, False, False, 10000),
        ])
        k = compute(v, EMPTY_COSTS, EMPTY_PAY, 90, ["month", "store"])
        self.assertTrue(k["new_return_rate"].isna().all())

    def test_same_customer_number_in_other_store_is_not_a_return(self):
        v = visits([
            ("2026-01-10", "s1", "A", "c1", True, False, False, 10000),
            ("2026-02-10", "s2", "B", "c1", False, False, False, 10000),
            ("2026-12-31", "s1", "A", "zz", False, False, False, 10000),
        ])
        self.assertFalse(new_return_flags(v, 90).iloc[0]["returned"])


class VisitCycle(unittest.TestCase):
    def test_median_days_since_previous_visit_in_same_store(self):
        v = visits([
            ("2026-07-01", "s", "A", "c1", True, False, False, 1),
            ("2026-08-15", "s", "A", "c1", False, True, False, 1),   # 45日
            ("2026-08-01", "s", "A", "c2", True, False, False, 1),
            ("2026-09-30", "s", "A", "c2", False, True, False, 1),   # 60日
            ("2026-09-01", "s", "A", "c1", False, True, False, 1),   # 17日
            ("2026-09-05", "s2", "B", "c2", True, False, False, 1),  # 別店舗なので周期に含めない
        ])
        k = compute(v, EMPTY_COSTS, EMPTY_PAY, 90, ["month", "store"]).set_index(["month", "store"])
        self.assertEqual(k.loc[("2026-09", "s"), "visit_cycle_days"], 38.5)
        self.assertEqual(k.loc[("2026-08", "s"), "visit_cycle_days"], 45)
        self.assertTrue(pd.isna(k.loc[("2026-09", "s2"), "visit_cycle_days"]))


class StoreKpi(unittest.TestCase):
    def test_basic_ratios_and_labor_cost(self):
        v = visits([
            ("2026-09-01", "s", "A", "c1", True, False, True, 12000),
            ("2026-09-02", "s", "A", "c2", False, True, False, 8000),
            ("2026-09-03", "s", "B", "c3", False, True, True, 10000),
            ("2026-09-04", "s", "B", "c4", False, False, False, 10000),
        ])
        costs = pd.DataFrame([{"month": "2026-09", "store": "s", "labor_cost": 16000, "hpb_cost": 5000}])
        pay = pd.DataFrame([{"month": "2026-09", "store": "s", "airpay_sales": 39000}])
        k = compute(v, costs, pay, 90, ["month", "store"]).iloc[0]
        self.assertEqual(k["sales"], 40000)
        self.assertEqual(k["avg_ticket"], 10000)
        self.assertAlmostEqual(k["nomination_rate"], 0.5)
        self.assertAlmostEqual(k["spa_rate"], 0.5)
        self.assertAlmostEqual(k["labor_cost_ratio"], 0.4)
        self.assertEqual(k["hpb_cost_per_new"], 5000)
        self.assertEqual(k["airpay_diff"], -1000)

    def test_staff_level_has_no_cost_columns(self):
        v = visits([("2026-09-01", "s", "A", "c1", True, False, False, 1000)])
        k = compute(v, EMPTY_COSTS, EMPTY_PAY, 90, ["month", "store", "staff"])
        self.assertNotIn("labor_cost_ratio", k.columns)


if __name__ == "__main__":
    unittest.main()
