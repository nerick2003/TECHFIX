import unittest
from datetime import datetime, timedelta
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from techfix import db
from techfix.accounting import AccountingEngine, JournalLine

class TestReversingSchedule(unittest.TestCase):
    def setUp(self):
        db.init_db(reset=True)
        self.eng = AccountingEngine()
        db.seed_chart_of_accounts(self.eng.conn)

    def tearDown(self):
        try:
            self.eng.close()
        except Exception:
            pass

    def test_template_approval_and_process(self):
        cash = db.get_account_by_name('Cash', self.eng.conn)['id']
        rev = db.get_account_by_name('Service Revenue', self.eng.conn)['id']
        util = db.get_account_by_name('Utilities Expense', self.eng.conn)['id']
        util_pay = db.get_account_by_name('Utilities Payable', self.eng.conn)['id']

        self.eng.record_entry(datetime.now().strftime('%Y-%m-%d'), 'Revenue', [
            JournalLine(account_id=cash, debit=500.0),
            JournalLine(account_id=rev, credit=500.0),
        ], status='posted')

        eid = self.eng.record_entry(datetime.now().strftime('%Y-%m-%d'), 'Accrue utilities', [
            JournalLine(account_id=util, debit=200.0),
            JournalLine(account_id=util_pay, credit=200.0),
        ], is_adjusting=True, status='posted')

        tpl_id = db.create_reversing_template('Utilities Accrual', entry_type='Accrual', required_fields={'memo': 'Reverse utilities accrual'}, default_memo='Reverse utilities accrual', authorization_level=1, approval_required=1, conn=self.eng.conn)
        rev_on = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        qid = self.eng.apply_reversing_template(eid, tpl_id, rev_on, memo='Reverse utilities', notes='Monthly reversal')

        db.add_reversing_approval(qid, reviewer='Controller', role='Finance', level=1, status='approved', approved_on=datetime.now().strftime('%Y-%m-%d'), conn=self.eng.conn)

        created = self.eng.process_reversing_schedule(as_of=rev_on)
        self.assertTrue(len(created) >= 1)

        report = self.eng.generate_reversing_report(as_of=rev_on)
        self.assertIn('summary', report)
        self.assertIsInstance(report['summary'], dict)

if __name__ == '__main__':
    unittest.main()
