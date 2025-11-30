import unittest
from datetime import date, timedelta
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from techfix import db
from techfix.accounting import AccountingEngine, JournalLine


class TechFixTests(unittest.TestCase):
    def setUp(self):
        db.init_db(reset=True)
        self.eng = AccountingEngine()
        db.seed_chart_of_accounts(self.eng.conn)

    def tearDown(self):
        try:
            self.eng.close()
        except Exception:
            pass

    def test_transaction_posting_cycle_status(self):
        cash = db.get_account_by_name('Cash', self.eng.conn)['id']
        svc = db.get_account_by_name('Service Revenue', self.eng.conn)['id']
        self.eng.record_entry(date.today().isoformat(), 'Post revenue', [
            JournalLine(account_id=cash, debit=100.0),
            JournalLine(account_id=svc, credit=100.0)
        ], status='posted')
        rows = db.get_cycle_status(self.eng.current_period_id, conn=self.eng.conn)
        s = {r['step']: r['status'] for r in rows}
        self.assertEqual(s.get(1), 'completed')
        self.assertEqual(s.get(2), 'completed')

    def test_trial_balance_activity(self):
        cash = db.get_account_by_name('Cash', self.eng.conn)['id']
        rent = db.get_account_by_name('Rent Expense', self.eng.conn)['id']
        svc = db.get_account_by_name('Service Revenue', self.eng.conn)['id']
        d = date.today().isoformat()
        cash = db.get_account_by_name('Cash', self.eng.conn)['id']
        db.insert_journal_entry(date=d, description='Revenue', lines=[(cash, 500.0, 0.0), (svc, 0.0, 500.0)], conn=self.eng.conn)
        db.insert_journal_entry(date=d, description='Rent', lines=[(rent, 200.0, 0.0), (cash, 0.0, 200.0)], conn=self.eng.conn)
        rows = db.compute_trial_balance(up_to_date=d, include_temporary=True, period_id=self.eng.current_period_id, conn=self.eng.conn)
        rev = sum((r['net_credit'] - r['net_debit']) for r in rows if r['type'].lower() == 'revenue')
        exp = sum((r['net_debit'] - r['net_credit']) for r in rows if r['type'].lower() == 'expense')
        self.assertAlmostEqual(rev, 500.0, places=2)
        self.assertAlmostEqual(exp, 200.0, places=2)

    def test_make_closing_entries(self):
        cash = db.get_account_by_name('Cash', self.eng.conn)['id']
        svc = db.get_account_by_name('Service Revenue', self.eng.conn)['id']
        rent = db.get_account_by_name('Rent Expense', self.eng.conn)['id']
        d = date.today().isoformat()
        db.insert_journal_entry(date=d, description='Revenue', lines=[(cash, 300.0, 0.0), (svc, 0.0, 300.0)], conn=self.eng.conn)
        db.insert_journal_entry(date=d, description='Rent', lines=[(rent, 150.0, 0.0), (cash, 0.0, 150.0)], conn=self.eng.conn)
        created = self.eng.make_closing_entries(d)
        self.assertTrue(len(created) >= 2)
        rows = db.get_cycle_status(self.eng.current_period_id, conn=self.eng.conn)
        s = {r['step']: r['status'] for r in rows}
        self.assertEqual(s.get(8), 'completed')
        self.assertEqual(s.get(9), 'in_progress')

    def test_reversing_schedule(self):
        exp = db.get_account_by_name('Rent Expense', self.eng.conn)['id']
        cash = db.get_account_by_name('Cash', self.eng.conn)['id']
        today = date.today().isoformat()
        rid = self.eng.record_entry(today, 'Accrual', [
            JournalLine(account_id=exp, debit=250.0),
            JournalLine(account_id=cash, credit=250.0)
        ], status='posted', schedule_reverse_on=today)
        q_before = [dict(r) for r in db.list_reversing_queue(self.eng.current_period_id, conn=self.eng.conn)]
        self.assertTrue(any(r['original_entry_id'] == rid and r['status'] == 'pending' for r in q_before))
        created = self.eng.process_reversing_schedule(today)
        self.assertTrue(len(created) >= 1)
        q_after = [dict(r) for r in db.list_reversing_queue(self.eng.current_period_id, conn=self.eng.conn)]
        self.assertTrue(any(r['original_entry_id'] == rid and r['status'] == 'completed' for r in q_after))

    def test_income_statement_range(self):
        svc = db.get_account_by_name('Service Revenue', self.eng.conn)['id']
        cash = db.get_account_by_name('Cash', self.eng.conn)['id']
        last = (date.today() - timedelta(days=30)).isoformat()
        today = date.today().isoformat()
        cash = db.get_account_by_name('Cash', self.eng.conn)['id']
        db.insert_journal_entry(date=last, description='Rev last', lines=[(cash, 400.0, 0.0), (svc, 0.0, 400.0)], conn=self.eng.conn)
        db.insert_journal_entry(date=today, description='Rev today', lines=[(cash, 600.0, 0.0), (svc, 0.0, 600.0)], conn=self.eng.conn)
        rows = db.compute_trial_balance(from_date=today, up_to_date=today, include_temporary=True, period_id=self.eng.current_period_id, conn=self.eng.conn)
        rev = sum((r['net_credit'] - r['net_debit']) for r in rows if r['type'].lower() == 'revenue')
        self.assertAlmostEqual(rev, 600.0, places=2)


if __name__ == '__main__':
    unittest.main()
