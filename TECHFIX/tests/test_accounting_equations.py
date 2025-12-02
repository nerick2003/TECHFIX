"""
Comprehensive test suite for accounting equations and logic.

This test file validates:
1. Double-entry bookkeeping (debits = credits)
2. Trial balance equation (total debits = total credits)
3. Income statement equation (Net Income = Revenue - Expenses)
4. Balance sheet equation (Assets = Liabilities + Equity)
5. Account balance calculations
6. Adjusting entries logic
7. Closing entries logic
8. Cash flow calculations
"""

import unittest
from datetime import date, timedelta
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from techfix import db
from techfix.accounting import AccountingEngine, JournalLine


class TestAccountingEquations(unittest.TestCase):
    """Test core accounting equations and logic."""

    def setUp(self):
        """Set up a fresh database for each test."""
        db.init_db(reset=True)
        self.eng = AccountingEngine()
        db.seed_chart_of_accounts(self.eng.conn)
        self.today = date.today().isoformat()

    def tearDown(self):
        """Clean up after each test."""
        try:
            self.eng.close()
        except Exception:
            pass

    def _get_account_id(self, name: str) -> int:
        """Helper to get account ID by name."""
        account = db.get_account_by_name(name, self.eng.conn)
        if account is None:
            raise ValueError(f"Account '{name}' not found")
        return account['id']

    def test_double_entry_bookkeeping(self):
        """Test that all journal entries maintain debits = credits."""
        cash = self._get_account_id('Cash')
        revenue = self._get_account_id('Service Revenue')
        expense = self._get_account_id('Rent Expense')
        ap = self._get_account_id('Accounts Payable')

        # Test 1: Simple revenue entry
        entry_id1 = self.eng.record_entry(
            self.today,
            'Service revenue',
            [
                JournalLine(account_id=cash, debit=1000.0),
                JournalLine(account_id=revenue, credit=1000.0),
            ],
            status='posted',
        )
        self.assertIsInstance(entry_id1, int)

        # Verify the entry is balanced
        cur = self.eng.conn.execute(
            "SELECT SUM(debit) as total_debit, SUM(credit) as total_credit "
            "FROM journal_lines WHERE entry_id = ?",
            (entry_id1,)
        )
        row = cur.fetchone()
        self.assertAlmostEqual(row['total_debit'], row['total_credit'], places=2)

        # Test 2: Expense entry
        entry_id2 = self.eng.record_entry(
            self.today,
            'Rent expense',
            [
                JournalLine(account_id=expense, debit=500.0),
                JournalLine(account_id=cash, credit=500.0),
            ],
            status='posted',
        )
        cur = self.eng.conn.execute(
            "SELECT SUM(debit) as total_debit, SUM(credit) as total_credit "
            "FROM journal_lines WHERE entry_id = ?",
            (entry_id2,)
        )
        row = cur.fetchone()
        self.assertAlmostEqual(row['total_debit'], row['total_credit'], places=2)

        # Test 3: Multi-line entry
        entry_id3 = self.eng.record_entry(
            self.today,
            'Purchase on account',
            [
                JournalLine(account_id=expense, debit=300.0),
                JournalLine(account_id=ap, credit=300.0),
            ],
            status='posted',
        )
        cur = self.eng.conn.execute(
            "SELECT SUM(debit) as total_debit, SUM(credit) as total_credit "
            "FROM journal_lines WHERE entry_id = ?",
            (entry_id3,)
        )
        row = cur.fetchone()
        self.assertAlmostEqual(row['total_debit'], row['total_credit'], places=2)

    def test_trial_balance_equation(self):
        """Test that trial balance maintains: Total Debits = Total Credits."""
        cash = self._get_account_id('Cash')
        revenue = self._get_account_id('Service Revenue')
        expense = self._get_account_id('Rent Expense')
        supplies = self._get_account_id('Supplies')
        ap = self._get_account_id('Accounts Payable')

        # Post several transactions
        self.eng.record_entry(
            self.today,
            'Owner investment',
            [
                JournalLine(account_id=cash, debit=10000.0),
                JournalLine(account_id=self._get_account_id("Owner's Capital"), credit=10000.0),
            ],
            status='posted',
        )

        self.eng.record_entry(
            self.today,
            'Service revenue',
            [
                JournalLine(account_id=cash, debit=5000.0),
                JournalLine(account_id=revenue, credit=5000.0),
            ],
            status='posted',
        )

        self.eng.record_entry(
            self.today,
            'Rent expense',
            [
                JournalLine(account_id=expense, debit=2000.0),
                JournalLine(account_id=cash, credit=2000.0),
            ],
            status='posted',
        )

        self.eng.record_entry(
            self.today,
            'Purchase supplies on account',
            [
                JournalLine(account_id=supplies, debit=1500.0),
                JournalLine(account_id=ap, credit=1500.0),
            ],
            status='posted',
        )

        # Compute trial balance
        rows = db.compute_trial_balance(
            period_id=self.eng.current_period_id,
            conn=self.eng.conn
        )

        total_debits = sum(float(r['net_debit'] or 0) for r in rows)
        total_credits = sum(float(r['net_credit'] or 0) for r in rows)

        # Core equation: Total Debits = Total Credits
        self.assertAlmostEqual(
            total_debits,
            total_credits,
            places=2,
            msg=f"Trial balance must balance: Debits={total_debits}, Credits={total_credits}"
        )

    def test_income_statement_equation(self):
        """Test Income Statement equation: Net Income = Total Revenue - Total Expenses."""
        cash = self._get_account_id('Cash')
        revenue = self._get_account_id('Service Revenue')
        rent_exp = self._get_account_id('Rent Expense')
        util_exp = self._get_account_id('Utilities Expense')
        sup_exp = self._get_account_id('Supplies Expense')

        # Post revenue transactions
        self.eng.record_entry(
            self.today,
            'Service revenue 1',
            [
                JournalLine(account_id=cash, debit=8000.0),
                JournalLine(account_id=revenue, credit=8000.0),
            ],
            status='posted',
        )

        self.eng.record_entry(
            self.today,
            'Service revenue 2',
            [
                JournalLine(account_id=cash, debit=2000.0),
                JournalLine(account_id=revenue, credit=2000.0),
            ],
            status='posted',
        )

        # Post expense transactions
        self.eng.record_entry(
            self.today,
            'Rent expense',
            [
                JournalLine(account_id=rent_exp, debit=3000.0),
                JournalLine(account_id=cash, credit=3000.0),
            ],
            status='posted',
        )

        self.eng.record_entry(
            self.today,
            'Utilities expense',
            [
                JournalLine(account_id=util_exp, debit=1000.0),
                JournalLine(account_id=cash, credit=1000.0),
            ],
            status='posted',
        )

        self.eng.record_entry(
            self.today,
            'Supplies expense',
            [
                JournalLine(account_id=sup_exp, debit=500.0),
                JournalLine(account_id=cash, credit=500.0),
            ],
            status='posted',
        )

        # Generate income statement
        start_date = (date.today() - timedelta(days=1)).isoformat()
        end_date = (date.today() + timedelta(days=1)).isoformat()
        income_stmt = self.eng.generate_income_statement(start_date, end_date)

        total_revenue = income_stmt['total_revenue']
        total_expense = income_stmt['total_expense']
        net_income = income_stmt['net_income']

        # Core equation: Net Income = Total Revenue - Total Expenses
        expected_net_income = total_revenue - total_expense
        self.assertAlmostEqual(
            net_income,
            expected_net_income,
            places=2,
            msg=f"Net Income equation: {net_income} should equal {total_revenue} - {total_expense} = {expected_net_income}"
        )

        # Verify expected values
        self.assertAlmostEqual(total_revenue, 10000.0, places=2)
        self.assertAlmostEqual(total_expense, 4500.0, places=2)
        self.assertAlmostEqual(net_income, 5500.0, places=2)

    def test_balance_sheet_equation(self):
        """Test Balance Sheet equation: Assets = Liabilities + Equity."""
        cash = self._get_account_id('Cash')
        ar = self._get_account_id('Accounts Receivable')
        supplies = self._get_account_id('Supplies')
        equip = self._get_account_id('Office Equipment')
        ap = self._get_account_id('Accounts Payable')
        capital = self._get_account_id("Owner's Capital")

        # Post transactions to create balances
        self.eng.record_entry(
            self.today,
            'Owner investment',
            [
                JournalLine(account_id=cash, debit=20000.0),
                JournalLine(account_id=capital, credit=20000.0),
            ],
            status='posted',
        )

        self.eng.record_entry(
            self.today,
            'Purchase equipment',
            [
                JournalLine(account_id=equip, debit=10000.0),
                JournalLine(account_id=cash, credit=10000.0),
            ],
            status='posted',
        )

        self.eng.record_entry(
            self.today,
            'Purchase supplies on account',
            [
                JournalLine(account_id=supplies, debit=2000.0),
                JournalLine(account_id=ap, credit=2000.0),
            ],
            status='posted',
        )

        # Note: We don't include revenue/expense in this test because
        # balance sheet only includes permanent accounts. Revenue/expense
        # need to be closed to equity first for the balance sheet to balance.

        # Generate balance sheet
        balance_sheet = self.eng.generate_balance_sheet(self.today)

        total_assets = balance_sheet['total_assets']
        total_liabilities = balance_sheet['total_liabilities']
        total_equity = balance_sheet['total_equity']
        balance_check = balance_sheet['balance_check']

        # Note: The balance sheet generation uses signed balances where:
        # - Assets: positive (debit balance)
        # - Liabilities: negative (credit balance, shown as negative in signed calculation)
        # - Equity: negative (credit balance, shown as negative in signed calculation)
        # So the equation becomes: Assets = -Liabilities + -Equity
        # Or: Assets + Liabilities + Equity = 0 (using signed values)
        
        # The balance sheet should balance for permanent accounts only
        # Assets: Cash (10000) + Equipment (10000) + Supplies (2000) = 22000
        # Liabilities: AP (-2000) in signed form
        # Equity: Capital (-20000) in signed form
        # Expected: 22000 + (-2000) + (-20000) = 0
        
        # Verify the equation using signed values: Assets + Liabilities + Equity = 0
        # This is the correct accounting equation when using signed balances
        signed_sum = total_assets + total_liabilities + total_equity
        self.assertAlmostEqual(
            signed_sum,
            0.0,
            places=2,
            msg=f"Balance sheet equation: Assets ({total_assets}) + Liabilities ({total_liabilities}) + Equity ({total_equity}) = {signed_sum} should equal 0"
        )
        
        # Also verify the traditional equation: Assets = |Liabilities| + |Equity|
        # (using absolute values since liabilities and equity are shown as negative in signed form)
        abs_liabilities = abs(total_liabilities)
        abs_equity = abs(total_equity)
        self.assertAlmostEqual(
            total_assets,
            abs_liabilities + abs_equity,
            places=2,
            msg=f"Balance sheet equation: Assets ({total_assets}) must equal |Liabilities| ({abs_liabilities}) + |Equity| ({abs_equity})"
        )

    def test_account_balance_calculations(self):
        """Test that account balances are calculated correctly based on account type."""
        cash = self._get_account_id('Cash')
        revenue = self._get_account_id('Service Revenue')
        expense = self._get_account_id('Rent Expense')
        ap = self._get_account_id('Accounts Payable')
        capital = self._get_account_id("Owner's Capital")

        # Post transactions
        self.eng.record_entry(
            self.today,
            'Owner investment',
            [
                JournalLine(account_id=cash, debit=5000.0),
                JournalLine(account_id=capital, credit=5000.0),
            ],
            status='posted',
        )

        self.eng.record_entry(
            self.today,
            'Service revenue',
            [
                JournalLine(account_id=cash, debit=3000.0),
                JournalLine(account_id=revenue, credit=3000.0),
            ],
            status='posted',
        )

        self.eng.record_entry(
            self.today,
            'Rent expense',
            [
                JournalLine(account_id=expense, debit=1000.0),
                JournalLine(account_id=cash, credit=1000.0),
            ],
            status='posted',
        )

        self.eng.record_entry(
            self.today,
            'Purchase on account',
            [
                JournalLine(account_id=expense, debit=500.0),
                JournalLine(account_id=ap, credit=500.0),
            ],
            status='posted',
        )

        # Get trial balance
        rows = db.compute_trial_balance(
            period_id=self.eng.current_period_id,
            conn=self.eng.conn
        )

        # Find account balances
        account_balances = {r['name']: r for r in rows}

        # Asset accounts: balance = debits - credits (should be positive for debit balance)
        cash_balance = account_balances['Cash']
        cash_net = cash_balance['net_debit'] - cash_balance['net_credit']
        self.assertAlmostEqual(cash_net, 7000.0, places=2, msg="Cash balance should be 5000 + 3000 - 1000 = 7000")

        # Revenue accounts: balance = credits - debits (should be positive for credit balance)
        revenue_balance = account_balances['Service Revenue']
        revenue_net = revenue_balance['net_credit'] - revenue_balance['net_debit']
        self.assertAlmostEqual(revenue_net, 3000.0, places=2, msg="Revenue balance should be 3000")

        # Expense accounts: balance = debits - credits (should be positive for debit balance)
        expense_balance = account_balances['Rent Expense']
        expense_net = expense_balance['net_debit'] - expense_balance['net_credit']
        self.assertAlmostEqual(expense_net, 1500.0, places=2, msg="Expense balance should be 1000 + 500 = 1500")

        # Liability accounts: balance = credits - debits (should be positive for credit balance)
        ap_balance = account_balances['Accounts Payable']
        ap_net = ap_balance['net_credit'] - ap_balance['net_debit']
        self.assertAlmostEqual(ap_net, 500.0, places=2, msg="AP balance should be 500")

        # Equity accounts: balance = credits - debits (should be positive for credit balance)
        capital_balance = account_balances["Owner's Capital"]
        capital_net = capital_balance['net_credit'] - capital_balance['net_debit']
        self.assertAlmostEqual(capital_net, 5000.0, places=2, msg="Capital balance should be 5000")

    def test_adjusting_entries_logic(self):
        """Test that adjusting entries work correctly."""
        supplies = self._get_account_id('Supplies')
        sup_exp = self._get_account_id('Supplies Expense')
        equip = self._get_account_id('Office Equipment')
        acc_dep = self._get_account_id('Accumulated Depreciation')
        dep_exp = self._get_account_id('Depreciation Expense')
        util_exp = self._get_account_id('Utilities Expense')
        util_pay = self._get_account_id('Utilities Payable')

        # Initial purchase of supplies
        self.eng.record_entry(
            self.today,
            'Purchase supplies',
            [
                JournalLine(account_id=supplies, debit=5000.0),
                JournalLine(account_id=self._get_account_id('Cash'), credit=5000.0),
            ],
            status='posted',
        )

        # Initial purchase of equipment
        self.eng.record_entry(
            self.today,
            'Purchase equipment',
            [
                JournalLine(account_id=equip, debit=20000.0),
                JournalLine(account_id=self._get_account_id('Cash'), credit=20000.0),
            ],
            status='posted',
        )

        # Adjusting entry 1: Supplies used
        self.eng.record_entry(
            self.today,
            'Adjust supplies used',
            [
                JournalLine(account_id=sup_exp, debit=2000.0),
                JournalLine(account_id=supplies, credit=2000.0),
            ],
            is_adjusting=True,
            status='posted',
        )

        # Adjusting entry 2: Depreciation
        self.eng.record_entry(
            self.today,
            'Record depreciation',
            [
                JournalLine(account_id=dep_exp, debit=1000.0),
                JournalLine(account_id=acc_dep, credit=1000.0),
            ],
            is_adjusting=True,
            status='posted',
        )

        # Adjusting entry 3: Accrue utilities
        self.eng.record_entry(
            self.today,
            'Accrue utilities',
            [
                JournalLine(account_id=util_exp, debit=500.0),
                JournalLine(account_id=util_pay, credit=500.0),
            ],
            is_adjusting=True,
            status='posted',
        )

        # Verify adjusting entries are marked correctly
        cur = self.eng.conn.execute(
            "SELECT COUNT(*) as count FROM journal_entries WHERE is_adjusting = 1"
        )
        self.assertEqual(cur.fetchone()['count'], 3)

        # Verify balances after adjustments
        rows = db.compute_trial_balance(
            period_id=self.eng.current_period_id,
            conn=self.eng.conn
        )
        account_balances = {r['name']: r for r in rows}

        # Supplies should be reduced
        supplies_balance = account_balances['Supplies']
        supplies_net = supplies_balance['net_debit'] - supplies_balance['net_credit']
        self.assertAlmostEqual(supplies_net, 3000.0, places=2, msg="Supplies should be 5000 - 2000 = 3000")

        # Supplies expense should be increased
        sup_exp_balance = account_balances['Supplies Expense']
        sup_exp_net = sup_exp_balance['net_debit'] - sup_exp_balance['net_credit']
        self.assertAlmostEqual(sup_exp_net, 2000.0, places=2, msg="Supplies expense should be 2000")

        # Accumulated depreciation should be increased
        acc_dep_balance = account_balances['Accumulated Depreciation']
        acc_dep_net = acc_dep_balance['net_credit'] - acc_dep_balance['net_debit']
        self.assertAlmostEqual(acc_dep_net, 1000.0, places=2, msg="Accumulated depreciation should be 1000")

        # Utilities payable should be increased
        util_pay_balance = account_balances['Utilities Payable']
        util_pay_net = util_pay_balance['net_credit'] - util_pay_balance['net_debit']
        self.assertAlmostEqual(util_pay_net, 500.0, places=2, msg="Utilities payable should be 500")

    def test_closing_entries_logic(self):
        """Test that closing entries properly close revenue and expense accounts."""
        cash = self._get_account_id('Cash')
        revenue = self._get_account_id('Service Revenue')
        rent_exp = self._get_account_id('Rent Expense')
        util_exp = self._get_account_id('Utilities Expense')
        capital = self._get_account_id("Owner's Capital")

        # Post revenue and expenses
        self.eng.record_entry(
            self.today,
            'Service revenue',
            [
                JournalLine(account_id=cash, debit=10000.0),
                JournalLine(account_id=revenue, credit=10000.0),
            ],
            status='posted',
        )

        self.eng.record_entry(
            self.today,
            'Rent expense',
            [
                JournalLine(account_id=rent_exp, debit=3000.0),
                JournalLine(account_id=cash, credit=3000.0),
            ],
            status='posted',
        )

        self.eng.record_entry(
            self.today,
            'Utilities expense',
            [
                JournalLine(account_id=util_exp, debit=2000.0),
                JournalLine(account_id=cash, credit=2000.0),
            ],
            status='posted',
        )

        # Get balances before closing
        rows_before = db.compute_trial_balance(
            period_id=self.eng.current_period_id,
            conn=self.eng.conn
        )
        account_balances_before = {r['name']: r for r in rows_before}

        revenue_before = account_balances_before['Service Revenue']
        revenue_net_before = revenue_before['net_credit'] - revenue_before['net_debit']

        # Make closing entries
        closing_entry_ids = self.eng.make_closing_entries(self.today)
        self.assertGreater(len(closing_entry_ids), 0, "Should create at least one closing entry")

        # Get balances after closing
        rows_after = db.compute_trial_balance(
            period_id=self.eng.current_period_id,
            conn=self.eng.conn
        )
        account_balances_after = {r['name']: r for r in rows_after}

        # Revenue and expense accounts should be closed (zero balance)
        revenue_after = account_balances_after['Service Revenue']
        revenue_net_after = revenue_after['net_credit'] - revenue_after['net_debit']
        self.assertAlmostEqual(revenue_net_after, 0.0, places=2, msg="Revenue should be closed to zero")

        rent_exp_after = account_balances_after['Rent Expense']
        rent_exp_net_after = rent_exp_after['net_debit'] - rent_exp_after['net_credit']
        self.assertAlmostEqual(rent_exp_net_after, 0.0, places=2, msg="Rent expense should be closed to zero")

        util_exp_after = account_balances_after['Utilities Expense']
        util_exp_net_after = util_exp_after['net_debit'] - util_exp_after['net_credit']
        self.assertAlmostEqual(util_exp_net_after, 0.0, places=2, msg="Utilities expense should be closed to zero")

        # Capital should be increased by net income
        capital_after = account_balances_after["Owner's Capital"]
        capital_net_after = capital_after['net_credit'] - capital_after['net_debit']
        # Net income = 10000 - 3000 - 2000 = 5000
        # Capital should increase by 5000 (from closing entries)
        self.assertGreater(capital_net_after, 0.0, msg="Capital should be increased by net income")

    def test_cash_flow_calculation(self):
        """Test cash flow statement calculations."""
        cash = self._get_account_id('Cash')
        revenue = self._get_account_id('Service Revenue')
        expense = self._get_account_id('Rent Expense')
        equip = self._get_account_id('Office Equipment')
        capital = self._get_account_id("Owner's Capital")
        ap = self._get_account_id('Accounts Payable')

        start_date = (date.today() - timedelta(days=1)).isoformat()
        end_date = (date.today() + timedelta(days=1)).isoformat()

        # Operating activity: Revenue (cash)
        self.eng.record_entry(
            self.today,
            'Service revenue',
            [
                JournalLine(account_id=cash, debit=5000.0),
                JournalLine(account_id=revenue, credit=5000.0),
            ],
            status='posted',
        )

        # Operating activity: Expense (cash)
        self.eng.record_entry(
            self.today,
            'Rent expense',
            [
                JournalLine(account_id=expense, debit=2000.0),
                JournalLine(account_id=cash, credit=2000.0),
            ],
            status='posted',
        )

        # Investing activity: Purchase equipment (cash)
        self.eng.record_entry(
            self.today,
            'Purchase equipment',
            [
                JournalLine(account_id=equip, debit=10000.0),
                JournalLine(account_id=cash, credit=10000.0),
            ],
            status='posted',
        )

        # Financing activity: Owner investment (cash)
        self.eng.record_entry(
            self.today,
            'Owner investment',
            [
                JournalLine(account_id=cash, debit=15000.0),
                JournalLine(account_id=capital, credit=15000.0),
            ],
            status='posted',
        )

        # Generate cash flow statement
        cash_flow = self.eng.generate_cash_flow(start_date, end_date)

        # Verify cash flow sections
        self.assertIn('sections', cash_flow)
        self.assertIn('totals', cash_flow)
        self.assertIn('net_change_in_cash', cash_flow)

        operating_total = cash_flow['totals']['Operating']
        investing_total = cash_flow['totals']['Investing']
        financing_total = cash_flow['totals']['Financing']
        net_change = cash_flow['net_change_in_cash']

        # Net change should equal sum of all sections
        expected_net_change = operating_total + investing_total + financing_total
        self.assertAlmostEqual(
            net_change,
            expected_net_change,
            places=2,
            msg=f"Net change in cash ({net_change}) should equal sum of sections ({expected_net_change})"
        )

        # Verify expected values
        # Operating: 5000 - 2000 = 3000
        self.assertAlmostEqual(operating_total, 3000.0, places=2)
        # Investing: -10000
        self.assertAlmostEqual(investing_total, -10000.0, places=2)
        # Financing: 15000
        self.assertAlmostEqual(financing_total, 15000.0, places=2)
        # Net change: 3000 - 10000 + 15000 = 8000
        self.assertAlmostEqual(net_change, 8000.0, places=2)

    def test_comprehensive_accounting_cycle(self):
        """Test a complete accounting cycle with all equations."""
        cash = self._get_account_id('Cash')
        revenue = self._get_account_id('Service Revenue')
        rent_exp = self._get_account_id('Rent Expense')
        supplies = self._get_account_id('Supplies')
        sup_exp = self._get_account_id('Supplies Expense')
        capital = self._get_account_id("Owner's Capital")
        ap = self._get_account_id('Accounts Payable')

        # Step 1: Post transactions
        self.eng.record_entry(
            self.today,
            'Owner investment',
            [
                JournalLine(account_id=cash, debit=20000.0),
                JournalLine(account_id=capital, credit=20000.0),
            ],
            status='posted',
        )

        self.eng.record_entry(
            self.today,
            'Service revenue',
            [
                JournalLine(account_id=cash, debit=15000.0),
                JournalLine(account_id=revenue, credit=15000.0),
            ],
            status='posted',
        )

        self.eng.record_entry(
            self.today,
            'Purchase supplies',
            [
                JournalLine(account_id=supplies, debit=5000.0),
                JournalLine(account_id=cash, credit=5000.0),
            ],
            status='posted',
        )

        self.eng.record_entry(
            self.today,
            'Rent expense',
            [
                JournalLine(account_id=rent_exp, debit=4000.0),
                JournalLine(account_id=cash, credit=4000.0),
            ],
            status='posted',
        )

        # Step 2: Verify trial balance balances
        rows = db.compute_trial_balance(
            period_id=self.eng.current_period_id,
            conn=self.eng.conn
        )
        total_debits = sum(float(r['net_debit'] or 0) for r in rows)
        total_credits = sum(float(r['net_credit'] or 0) for r in rows)
        self.assertAlmostEqual(total_debits, total_credits, places=2)

        # Step 3: Post adjusting entry
        self.eng.record_entry(
            self.today,
            'Adjust supplies used',
            [
                JournalLine(account_id=sup_exp, debit=2000.0),
                JournalLine(account_id=supplies, credit=2000.0),
            ],
            is_adjusting=True,
            status='posted',
        )

        # Step 4: Verify adjusted trial balance still balances
        rows_adjusted = db.compute_trial_balance(
            period_id=self.eng.current_period_id,
            conn=self.eng.conn
        )
        total_debits_adj = sum(float(r['net_debit'] or 0) for r in rows_adjusted)
        total_credits_adj = sum(float(r['net_credit'] or 0) for r in rows_adjusted)
        self.assertAlmostEqual(total_debits_adj, total_credits_adj, places=2)

        # Step 5: Generate income statement
        start_date = (date.today() - timedelta(days=1)).isoformat()
        end_date = (date.today() + timedelta(days=1)).isoformat()
        income_stmt = self.eng.generate_income_statement(start_date, end_date)
        net_income = income_stmt['net_income']
        expected_net = income_stmt['total_revenue'] - income_stmt['total_expense']
        self.assertAlmostEqual(net_income, expected_net, places=2)

        # Step 6: Close accounts before generating balance sheet
        # Balance sheet only includes permanent accounts, so we need to close
        # revenue/expense accounts to equity first
        closing_ids = self.eng.make_closing_entries(self.today)
        self.assertGreater(len(closing_ids), 0)

        # Step 7: Generate balance sheet (now that accounts are closed)
        balance_sheet = self.eng.generate_balance_sheet(self.today)
        balance_check = balance_sheet['balance_check']
        # Note: Balance sheet uses signed balances, so Assets + Liabilities + Equity = 0
        signed_sum = balance_sheet['total_assets'] + balance_sheet['total_liabilities'] + balance_sheet['total_equity']
        self.assertAlmostEqual(signed_sum, 0.0, places=2)

        # Step 8: Verify post-closing trial balance still balances
        rows_post_closing = db.compute_trial_balance(
            period_id=self.eng.current_period_id,
            conn=self.eng.conn
        )
        total_debits_pc = sum(float(r['net_debit'] or 0) for r in rows_post_closing)
        total_credits_pc = sum(float(r['net_credit'] or 0) for r in rows_post_closing)
        self.assertAlmostEqual(total_debits_pc, total_credits_pc, places=2)


if __name__ == '__main__':
    unittest.main()

