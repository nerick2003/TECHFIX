import unittest
from datetime import date, timedelta
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from techfix import db
from techfix.accounting import AccountingEngine, JournalLine


class TestDuplicateProtectionAndCashFlow(unittest.TestCase):
    def setUp(self) -> None:
        db.init_db(reset=True)
        self.eng = AccountingEngine()
        db.seed_chart_of_accounts(self.eng.conn)

    def tearDown(self) -> None:
        try:
            self.eng.close()
        except Exception:
            pass

    def test_cash_flow_positive_net_change(self) -> None:
        """Basic sanity check: cash inflow increases net change in cash."""
        cash = db.get_account_by_name("Cash", self.eng.conn)["id"]
        svc = db.get_account_by_name("Service Revenue", self.eng.conn)["id"]
        today = date.today().isoformat()
        self.eng.record_entry(
            today,
            "Cash sale",
            [
                JournalLine(account_id=cash, debit=1000.0),
                JournalLine(account_id=svc, credit=1000.0),
            ],
            status="posted",
        )
        cf = self.eng.generate_cash_flow(today, today)
        self.assertIsInstance(cf, dict)
        self.assertIn("net_change_in_cash", cf)
        self.assertGreaterEqual(cf["net_change_in_cash"], 1000.0 - 0.01)

    def test_cash_flow_zero_when_no_activity(self) -> None:
        """If no journal entries exist in range, net change in cash should be ~0."""
        today = date.today().isoformat()
        cf = self.eng.generate_cash_flow(today, today)
        self.assertIsInstance(cf, dict)
        self.assertAlmostEqual(cf.get("net_change_in_cash", 0.0), 0.0, places=2)


if __name__ == "__main__":
    unittest.main()


