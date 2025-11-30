import unittest
from datetime import datetime, timedelta
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from techfix.accounting import AccountingEngine, JournalLine
from techfix import db

class TestAccountingCycle(unittest.TestCase):
    def setUp(self):
        self.engine = AccountingEngine()

    def tearDown(self):
        try:
            self.engine.close()
        except Exception:
            pass

    def _get_statuses(self):
        rows = self.engine.get_cycle_status()
        return {int(r['step']): r['status'] for r in rows}

    def test_full_cycle(self):
        today = datetime.now().strftime('%Y-%m-%d')
        cash = db.get_account_by_name('Cash', self.engine.conn)
        rev = db.get_account_by_name('Service Revenue', self.engine.conn)
        sup = db.get_account_by_name('Supplies', self.engine.conn)
        ap = db.get_account_by_name('Accounts Payable', self.engine.conn)
        self.assertIsNotNone(cash)
        self.assertIsNotNone(rev)
        self.assertIsNotNone(sup)
        self.assertIsNotNone(ap)

        eid1 = self.engine.record_entry(
            today,
            'Revenue entry',
            [
                JournalLine(account_id=cash['id'], debit=1000.0),
                JournalLine(account_id=rev['id'], credit=1000.0),
            ],
            status='posted',
        )
        self.assertIsInstance(eid1, int)

        eid2 = self.engine.record_entry(
            today,
            'Purchase supplies on account',
            [
                JournalLine(account_id=sup['id'], debit=300.0),
                JournalLine(account_id=ap['id'], credit=300.0),
            ],
            status='posted',
        )
        self.assertIsInstance(eid2, int)

        rows = list(db.compute_trial_balance(period_id=self.engine.current_period_id, conn=self.engine.conn))
        snap1 = self.engine.capture_trial_balance_snapshot('unadjusted', today, rows)
        self.assertIsInstance(snap1, int)
        self.engine.set_cycle_step_status(3, 'completed', 'Posted to ledger')
        self.engine.set_cycle_step_status(4, 'completed', 'Prepared unadjusted trial balance')

        # Post an adjusting entry explicitly
        adj_amt = 100.0
        adj_id = self.engine.record_entry(
            today,
            'Adjust supplies used',
            [
                JournalLine(account_id=db.get_account_by_name('Supplies Expense', self.engine.conn)['id'], debit=adj_amt),
                JournalLine(account_id=sup['id'], credit=adj_amt),
            ],
            is_adjusting=True,
            status='posted',
        )
        self.assertIsInstance(adj_id, int)
        rows2 = list(db.compute_trial_balance(period_id=self.engine.current_period_id, conn=self.engine.conn))
        snap2 = self.engine.capture_trial_balance_snapshot('adjusted', today, rows2)
        self.assertIsInstance(snap2, int)
        self.engine.set_cycle_step_status(6, 'completed', 'Prepared adjusted trial balance')

        self.engine.set_cycle_step_status(7, 'completed', 'Financial statements prepared')

        closed_ids = self.engine.make_closing_entries(today)
        self.assertIsInstance(closed_ids, list)

        rows3 = list(db.compute_trial_balance(period_id=self.engine.current_period_id, conn=self.engine.conn))
        snap3 = self.engine.capture_trial_balance_snapshot('post_closing', today, rows3)
        self.assertIsInstance(snap3, int)
        self.engine.set_cycle_step_status(9, 'completed', 'Post-closing trial balance prepared')

        next_day = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        db.schedule_reversing_entry(eid1, next_day, conn=self.engine.conn)
        created = self.engine.process_reversing_schedule(as_of=next_day)
        self.assertIsInstance(created, list)

        statuses = self._get_statuses()
        for s in range(1, 10):
            self.assertIn(s, statuses)
        self.assertIn(10, statuses)

if __name__ == '__main__':
    unittest.main()
