"""
Test script to verify the accounting cycle with 15 entries.
Tests the complete flow from transactions through closing entries.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import date, timedelta
from techfix import db
from techfix.accounting import AccountingEngine, JournalLine

# Fix Windows console encoding for peso symbol
PESO_SYMBOL = "PHP "
try:
    if sys.platform == 'win32':
        import io
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        PESO_SYMBOL = "₱ "
except Exception:
    PESO_SYMBOL = "PHP "


def get_account_id(eng, name):
    """Helper to get account ID by name."""
    account = db.get_account_by_name(name, eng.conn)
    if account is None:
        raise ValueError(f"Account '{name}' not found in database")
    return account['id']


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_entry_summary(entry_num, date, description, debit_total, credit_total):
    """Print a summary of a journal entry."""
    print(f"\nEntry {entry_num}: {date} - {description}")
    print(f"  Debit:  {PESO_SYMBOL}{debit_total:>12,.2f}")
    print(f"  Credit: {PESO_SYMBOL}{credit_total:>12,.2f}")
    diff = abs(debit_total - credit_total)
    if diff < 0.01:
        print(f"  ✓ Balanced")
    else:
        print(f"  ✗ NOT BALANCED (Difference: {PESO_SYMBOL}{diff:,.2f})")


def main():
    print_section("TESTING 15 ENTRIES - ACCOUNTING CYCLE VERIFICATION")
    
    # Initialize database
    print("\n1. Initializing database...")
    db.init_db(reset=True)
    eng = AccountingEngine()
    db.seed_chart_of_accounts(eng.conn)
    print("   ✓ Database initialized and chart of accounts seeded")
    
    # Get account IDs
    print("\n2. Loading account IDs...")
    accounts = {}
    account_names = [
        'Cash', "Owner's Capital", 'Supplies', 'Office Equipment',
        'Accounts Payable', 'Accounts Receivable', 'Service Revenue',
        'Utilities Expense', 'Rent Expense', "Owner's Drawings",
        'Supplies Expense', 'Depreciation Expense', 'Accumulated Depreciation',
        'Utilities Payable', 'Salaries & Wages', 'SSS, PhilHealth, and Pag-Ibig Payable'
    ]
    
    for name in account_names:
        accounts[name] = get_account_id(eng, name)
    print(f"   ✓ Loaded {len(accounts)} accounts")
    
    # Helper function to post entries
    def post(date_str, description, lines, is_adjusting=False, is_closing=False):
        """Post a journal entry."""
        journal_lines = [JournalLine(account_id=acc_id, debit=debit, credit=credit) 
                        for acc_id, debit, credit in lines]
        return eng.record_entry(
            date_str,
            description,
            journal_lines,
            is_adjusting=is_adjusting,
            is_closing=is_closing,
            status='posted'
        )
    
    # Set up dates
    year = date.today().year
    base_date = date(year, 1, 1)
    
    print_section("PHASE 1: REGULAR TRANSACTIONS (Entries 1-10)")
    
    entry_count = 0
    entry_ids = []
    
    # Entry 1: Owner investment
    entry_count += 1
    entry_ids.append(post(
        (base_date + timedelta(days=0)).isoformat(),
        'Owner investment',
        [(accounts['Cash'], 150000.0, 0.0), (accounts["Owner's Capital"], 0.0, 150000.0)]
    ))
    print_entry_summary(entry_count, base_date + timedelta(days=0), 'Owner investment', 150000.0, 150000.0)
    
    # Entry 2: Purchase supplies for cash
    entry_count += 1
    entry_ids.append(post(
        (base_date + timedelta(days=2)).isoformat(),
        'Purchase supplies (cash)',
        [(accounts['Supplies'], 8000.0, 0.0), (accounts['Cash'], 0.0, 8000.0)]
    ))
    print_entry_summary(entry_count, base_date + timedelta(days=2), 'Purchase supplies (cash)', 8000.0, 8000.0)
    
    # Entry 3: Purchase equipment on account
    entry_count += 1
    entry_ids.append(post(
        (base_date + timedelta(days=5)).isoformat(),
        'Purchase office equipment on account',
        [(accounts['Office Equipment'], 50000.0, 0.0), (accounts['Accounts Payable'], 0.0, 50000.0)]
    ))
    print_entry_summary(entry_count, base_date + timedelta(days=5), 'Purchase office equipment on account', 50000.0, 50000.0)
    
    # Entry 4: Service revenue (cash)
    entry_count += 1
    entry_ids.append(post(
        (base_date + timedelta(days=10)).isoformat(),
        'Service revenue (cash)',
        [(accounts['Cash'], 25000.0, 0.0), (accounts['Service Revenue'], 0.0, 25000.0)]
    ))
    print_entry_summary(entry_count, base_date + timedelta(days=10), 'Service revenue (cash)', 25000.0, 25000.0)
    
    # Entry 5: Service revenue (billed)
    entry_count += 1
    entry_ids.append(post(
        (base_date + timedelta(days=12)).isoformat(),
        'Service revenue (billed)',
        [(accounts['Accounts Receivable'], 35000.0, 0.0), (accounts['Service Revenue'], 0.0, 35000.0)]
    ))
    print_entry_summary(entry_count, base_date + timedelta(days=12), 'Service revenue (billed)', 35000.0, 35000.0)
    
    # Entry 6: Pay rent expense
    entry_count += 1
    entry_ids.append(post(
        (base_date + timedelta(days=15)).isoformat(),
        'Paid rent expense',
        [(accounts['Rent Expense'], 12000.0, 0.0), (accounts['Cash'], 0.0, 12000.0)]
    ))
    print_entry_summary(entry_count, base_date + timedelta(days=15), 'Paid rent expense', 12000.0, 12000.0)
    
    # Entry 7: Pay utilities expense
    entry_count += 1
    entry_ids.append(post(
        (base_date + timedelta(days=18)).isoformat(),
        'Paid utilities expense',
        [(accounts['Utilities Expense'], 5000.0, 0.0), (accounts['Cash'], 0.0, 5000.0)]
    ))
    print_entry_summary(entry_count, base_date + timedelta(days=18), 'Paid utilities expense', 5000.0, 5000.0)
    
    # Entry 8: Pay salaries
    entry_count += 1
    entry_ids.append(post(
        (base_date + timedelta(days=20)).isoformat(),
        'Paid salaries',
        [(accounts['Salaries & Wages'], 20000.0, 0.0), (accounts['Cash'], 0.0, 20000.0)]
    ))
    print_entry_summary(entry_count, base_date + timedelta(days=20), 'Paid salaries', 20000.0, 20000.0)
    
    # Entry 9: Received collection from AR
    entry_count += 1
    entry_ids.append(post(
        (base_date + timedelta(days=22)).isoformat(),
        'Received collection from accounts receivable',
        [(accounts['Cash'], 20000.0, 0.0), (accounts['Accounts Receivable'], 0.0, 20000.0)]
    ))
    print_entry_summary(entry_count, base_date + timedelta(days=22), 'Received collection from AR', 20000.0, 20000.0)
    
    # Entry 10: Paid accounts payable
    entry_count += 1
    entry_ids.append(post(
        (base_date + timedelta(days=25)).isoformat(),
        'Paid accounts payable',
        [(accounts['Accounts Payable'], 30000.0, 0.0), (accounts['Cash'], 0.0, 30000.0)]
    ))
    print_entry_summary(entry_count, base_date + timedelta(days=25), 'Paid accounts payable', 30000.0, 30000.0)
    
    print_section("PHASE 2: UNADJUSTED TRIAL BALANCE")
    
    # Generate unadjusted trial balance
    rows = list(db.compute_trial_balance(
        period_id=eng.current_period_id,
        include_temporary=True,
        conn=eng.conn
    ))
    
    total_debits = sum(float(r['net_debit'] or 0) for r in rows)
    total_credits = sum(float(r['net_credit'] or 0) for r in rows)
    diff = abs(total_debits - total_credits)
    
    print(f"\nTotal Debits:  {PESO_SYMBOL}{total_debits:>15,.2f}")
    print(f"Total Credits: {PESO_SYMBOL}{total_credits:>15,.2f}")
    print(f"Difference:    {PESO_SYMBOL}{diff:>15,.2f}")
    
    if diff < 0.01:
        print("✓ Unadjusted Trial Balance is BALANCED")
    else:
        print("✗ Unadjusted Trial Balance is NOT BALANCED")
        print("\nERROR: Entries are not balanced. Cannot proceed.")
        eng.close()
        return
    
    # Capture snapshot
    eng.capture_trial_balance_snapshot('unadjusted', base_date.isoformat(), rows)
    eng.set_cycle_step_status(4, 'completed', 'Unadjusted trial balance prepared')
    
    print_section("PHASE 3: ADJUSTING ENTRIES (Entries 11-13)")
    
    # Entry 11: Adjust supplies used
    entry_count += 1
    # Calculate supplies used: 8000 purchased - 3000 remaining = 5000 used
    remaining_supplies = 3000.0
    supplies_used = 8000.0 - remaining_supplies
    entry_ids.append(post(
        (base_date + timedelta(days=28)).isoformat(),
        'Adjust supplies used',
        [(accounts['Supplies Expense'], supplies_used, 0.0), (accounts['Supplies'], 0.0, supplies_used)],
        is_adjusting=True
    ))
    print_entry_summary(entry_count, base_date + timedelta(days=28), 'Adjust supplies used', supplies_used, supplies_used)
    
    # Entry 12: Record depreciation
    entry_count += 1
    depreciation_amount = 1000.0
    entry_ids.append(post(
        (base_date + timedelta(days=28)).isoformat(),
        'Record depreciation expense',
        [(accounts['Depreciation Expense'], depreciation_amount, 0.0), 
         (accounts['Accumulated Depreciation'], 0.0, depreciation_amount)],
        is_adjusting=True
    ))
    print_entry_summary(entry_count, base_date + timedelta(days=28), 'Record depreciation expense', depreciation_amount, depreciation_amount)
    
    # Entry 13: Accrue utilities expense
    entry_count += 1
    accrued_utilities = 2000.0
    entry_ids.append(post(
        (base_date + timedelta(days=28)).isoformat(),
        'Accrue utilities expense',
        [(accounts['Utilities Expense'], accrued_utilities, 0.0), 
         (accounts['Utilities Payable'], 0.0, accrued_utilities)],
        is_adjusting=True
    ))
    print_entry_summary(entry_count, base_date + timedelta(days=28), 'Accrue utilities expense', accrued_utilities, accrued_utilities)
    
    print_section("PHASE 4: ADJUSTED TRIAL BALANCE")
    
    # Generate adjusted trial balance
    rows_adj = list(db.compute_trial_balance(
        period_id=eng.current_period_id,
        include_temporary=True,
        conn=eng.conn
    ))
    
    total_debits_adj = sum(float(r['net_debit'] or 0) for r in rows_adj)
    total_credits_adj = sum(float(r['net_credit'] or 0) for r in rows_adj)
    diff_adj = abs(total_debits_adj - total_credits_adj)
    
    print(f"\nTotal Debits:  {PESO_SYMBOL}{total_debits_adj:>15,.2f}")
    print(f"Total Credits: {PESO_SYMBOL}{total_credits_adj:>15,.2f}")
    print(f"Difference:    {PESO_SYMBOL}{diff_adj:>15,.2f}")
    
    if diff_adj < 0.01:
        print("✓ Adjusted Trial Balance is BALANCED")
    else:
        print("✗ Adjusted Trial Balance is NOT BALANCED")
        print("\nERROR: Adjusted entries are not balanced. Cannot proceed.")
        eng.close()
        return
    
    # Capture snapshot
    eng.capture_trial_balance_snapshot('adjusted', base_date.isoformat(), rows_adj)
    eng.set_cycle_step_status(6, 'completed', 'Adjusted trial balance prepared')
    
    print_section("PHASE 5: FINANCIAL STATEMENTS")
    
    # Generate income statement
    end_date = (base_date + timedelta(days=28)).isoformat()
    income_stmt = eng.generate_income_statement(base_date.isoformat(), end_date)
    
    print("\nINCOME STATEMENT")
    print(f"Period: {base_date.isoformat()} to {end_date}")
    print("\nRevenues:")
    for rev in income_stmt['revenues']:
        print(f"  {rev['name']:<40} {PESO_SYMBOL}{rev['amount']:>12,.2f}")
    print(f"\nTotal Revenue:                    {PESO_SYMBOL}{income_stmt['total_revenue']:>12,.2f}")
    
    print("\nExpenses:")
    for exp in income_stmt['expenses']:
        print(f"  {exp['name']:<40} {PESO_SYMBOL}{exp['amount']:>12,.2f}")
    print(f"\nTotal Expenses:                   {PESO_SYMBOL}{income_stmt['total_expense']:>12,.2f}")
    print(f"\nNet Income:                       {PESO_SYMBOL}{income_stmt['net_income']:>12,.2f}")
    
    eng.set_cycle_step_status(7, 'completed', 'Financial statements prepared')
    
    print_section("PHASE 6: CLOSING ENTRIES (Entries 14-15)")
    
    # Generate closing entries
    closing_date = (base_date + timedelta(days=31)).isoformat()
    closing_entry_ids = eng.make_closing_entries(closing_date)
    
    print(f"\nGenerated {len(closing_entry_ids)} closing entries")
    entry_count += len(closing_entry_ids)
    
    # Show closing entries
    for i, cid in enumerate(closing_entry_ids, 1):
        cur = eng.conn.execute("""
            SELECT description, 
                   SUM(jl.debit) as total_debit,
                   SUM(jl.credit) as total_credit
            FROM journal_entries je
            JOIN journal_lines jl ON jl.entry_id = je.id
            WHERE je.id = ?
            GROUP BY je.id
        """, (cid,))
        result = cur.fetchone()
        if result:
            print_entry_summary(
                entry_count - len(closing_entry_ids) + i,
                closing_date,
                result['description'],
                float(result['total_debit'] or 0),
                float(result['total_credit'] or 0)
            )
    
    print_section("PHASE 7: POST-CLOSING TRIAL BALANCE")
    
    # Generate post-closing trial balance
    rows_pc = list(db.compute_trial_balance(
        period_id=eng.current_period_id,
        include_temporary=False,
        conn=eng.conn
    ))
    
    total_debits_pc = sum(float(r['net_debit'] or 0) for r in rows_pc)
    total_credits_pc = sum(float(r['net_credit'] or 0) for r in rows_pc)
    diff_pc = abs(total_debits_pc - total_credits_pc)
    
    print(f"\nTotal Debits:  {PESO_SYMBOL}{total_debits_pc:>15,.2f}")
    print(f"Total Credits: {PESO_SYMBOL}{total_credits_pc:>15,.2f}")
    print(f"Difference:    {PESO_SYMBOL}{diff_pc:>15,.2f}")
    
    if diff_pc < 0.01:
        print("✓ Post-Closing Trial Balance is BALANCED")
    else:
        print("✗ Post-Closing Trial Balance is NOT BALANCED")
    
    # Capture snapshot
    eng.capture_trial_balance_snapshot('post_closing', closing_date, rows_pc)
    eng.set_cycle_step_status(9, 'completed', 'Post-closing trial balance prepared')
    
    print_section("PHASE 8: BALANCE SHEET")
    
    # Generate balance sheet
    balance_sheet = eng.generate_balance_sheet(closing_date)
    
    print(f"\nBalance Sheet as of: {closing_date}")
    print("\nASSETS:")
    for asset in balance_sheet['assets']:
        print(f"  {asset['name']:<40} {PESO_SYMBOL}{asset['amount']:>12,.2f}")
    print(f"\nTotal Assets:                      {PESO_SYMBOL}{balance_sheet['total_assets']:>12,.2f}")
    
    print("\nLIABILITIES:")
    if balance_sheet['liabilities']:
        for liab in balance_sheet['liabilities']:
            print(f"  {liab['name']:<40} {PESO_SYMBOL}{liab['amount']:>12,.2f}")
    else:
        print("  (none)")
    print(f"\nTotal Liabilities:                 {PESO_SYMBOL}{balance_sheet['total_liabilities']:>12,.2f}")
    
    print("\nEQUITY:")
    for eq in balance_sheet['equity']:
        print(f"  {eq['name']:<40} {PESO_SYMBOL}{eq['amount']:>12,.2f}")
    print(f"\nTotal Equity:                      {PESO_SYMBOL}{balance_sheet['total_equity']:>12,.2f}")
    
    print(f"\nBalance Check (Assets - Liabilities - Equity): {PESO_SYMBOL}{balance_sheet['balance_check']:>12,.2f}")
    
    if abs(balance_sheet['balance_check']) < 0.01:
        print("✓ Balance Sheet is BALANCED")
    else:
        print("✗ Balance Sheet is NOT BALANCED")
    
    print_section("FINAL SUMMARY")
    
    print(f"\n✓ Total Entries Created: {entry_count}")
    print(f"  - Regular transactions: 10")
    print(f"  - Adjusting entries: 3")
    print(f"  - Closing entries: {len(closing_entry_ids)}")
    
    print(f"\n✓ Accounting Cycle Status:")
    statuses = eng.get_cycle_status()
    for status in statuses:
        step_name = {
            1: "Source Documents",
            2: "Journalization",
            3: "Posting to Ledger",
            4: "Unadjusted Trial Balance",
            5: "Adjusting Entries",
            6: "Adjusted Trial Balance",
            7: "Financial Statements",
            8: "Closing Entries",
            9: "Post-Closing Trial Balance",
            10: "Reversing Entries"
        }.get(int(status['step']), f"Step {status['step']}")
        print(f"  Step {status['step']:2d} ({step_name:<30}): {status['status']}")
    
    print(f"\n✓ Verification Results:")
    print(f"  - Unadjusted Trial Balance: {'BALANCED' if diff < 0.01 else 'NOT BALANCED'}")
    print(f"  - Adjusted Trial Balance: {'BALANCED' if diff_adj < 0.01 else 'NOT BALANCED'}")
    print(f"  - Post-Closing Trial Balance: {'BALANCED' if diff_pc < 0.01 else 'NOT BALANCED'}")
    print(f"  - Balance Sheet: {'BALANCED' if abs(balance_sheet['balance_check']) < 0.01 else 'NOT BALANCED'}")
    
    all_balanced = (diff < 0.01 and diff_adj < 0.01 and diff_pc < 0.01 and 
                   abs(balance_sheet['balance_check']) < 0.01)
    
    if all_balanced:
        print("\n" + "=" * 80)
        print("  ✓ ALL TESTS PASSED - ACCOUNTING CYCLE IS WORKING CORRECTLY")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("  ✗ SOME TESTS FAILED - PLEASE REVIEW THE ISSUES ABOVE")
        print("=" * 80)
    
    eng.close()


if __name__ == '__main__':
    main()

