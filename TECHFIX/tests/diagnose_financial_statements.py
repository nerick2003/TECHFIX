"""
Diagnostic script to check why income statement and cash flow show zero.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from techfix import db
from techfix.accounting import AccountingEngine
from datetime import date, datetime

# Fix Windows console encoding
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


def main():
    print("=" * 80)
    print("FINANCIAL STATEMENTS DIAGNOSTIC")
    print("=" * 80)
    print()
    
    eng = AccountingEngine()
    
    try:
        # Check current period
        print("1. CHECKING CURRENT PERIOD")
        print("-" * 80)
        if not eng.current_period_id:
            print("✗ ERROR: No active accounting period!")
            return
        
        print(f"✓ Current Period ID: {eng.current_period_id}")
        if eng.current_period:
            period_name = eng.current_period['name'] if 'name' in eng.current_period.keys() else 'N/A'
            period_start = eng.current_period['start_date'] if 'start_date' in eng.current_period.keys() else 'N/A'
            period_end = eng.current_period['end_date'] if 'end_date' in eng.current_period.keys() else 'N/A'
            print(f"  Period Name: {period_name}")
            print(f"  Start Date: {period_start}")
            print(f"  End Date: {period_end}")
        print()
        
        # Check journal entries
        print("2. CHECKING JOURNAL ENTRIES")
        print("-" * 80)
        cur = eng.conn.execute("""
            SELECT COUNT(*) as count,
                   MIN(date) as min_date,
                   MAX(date) as max_date,
                   SUM(CASE WHEN status = 'posted' THEN 1 ELSE 0 END) as posted_count
            FROM journal_entries
            WHERE period_id = ?
        """, (eng.current_period_id,))
        
        entry_stats = cur.fetchone()
        total_entries = entry_stats['count'] or 0
        min_date = entry_stats['min_date']
        max_date = entry_stats['max_date']
        posted_count = entry_stats['posted_count'] or 0
        
        print(f"Total Entries: {total_entries}")
        print(f"Posted Entries: {posted_count}")
        print(f"Date Range: {min_date} to {max_date}")
        
        if total_entries == 0:
            print("✗ ERROR: No journal entries found in current period!")
            return
        
        if posted_count == 0:
            print("✗ ERROR: No posted entries found!")
            return
        
        print()
        
        # Check revenue and expense accounts
        print("3. CHECKING REVENUE AND EXPENSE ACCOUNTS")
        print("-" * 80)
        cur = eng.conn.execute("""
            SELECT a.name, a.type,
                   COALESCE(SUM(jl.debit), 0) as total_debit,
                   COALESCE(SUM(jl.credit), 0) as total_credit
            FROM accounts a
            LEFT JOIN journal_lines jl ON jl.account_id = a.id
            LEFT JOIN journal_entries je ON je.id = jl.entry_id
            WHERE a.type IN ('Revenue', 'Expense')
              AND a.is_active = 1
              AND (je.period_id = ? OR je.period_id IS NULL)
              AND (je.status = 'posted' OR je.status IS NULL)
              AND (je.is_closing = 0 OR je.is_closing IS NULL)  -- exclude closing entries so revenues/expenses don't net to zero
            GROUP BY a.id, a.name, a.type
            ORDER BY a.type, a.name
        """, (eng.current_period_id,))
        
        revenue_accounts = []
        expense_accounts = []
        
        for row in cur.fetchall():
            acc_type = row['type'].lower()
            net_debit = float(row['total_debit'] or 0)
            net_credit = float(row['total_credit'] or 0)
            
            if acc_type == 'revenue':
                balance = net_credit - net_debit
                if abs(balance) > 0.01:
                    revenue_accounts.append((row['name'], balance))
            elif acc_type == 'expense':
                balance = net_debit - net_credit
                if abs(balance) > 0.01:
                    expense_accounts.append((row['name'], balance))
        
        print(f"Revenue Accounts with Activity: {len(revenue_accounts)}")
        for name, bal in revenue_accounts:
            print(f"  {name}: {PESO_SYMBOL}{bal:,.2f}")
        
        print(f"\nExpense Accounts with Activity: {len(expense_accounts)}")
        for name, bal in expense_accounts:
            print(f"  {name}: {PESO_SYMBOL}{bal:,.2f}")
        
        if len(revenue_accounts) == 0 and len(expense_accounts) == 0:
            print("\n✗ WARNING: No revenue or expense activity found!")
        print()
        
        # Test income statement generation
        print("4. TESTING INCOME STATEMENT GENERATION")
        print("-" * 80)
        
        # Use date range from entries
        period_start = None
        if eng.current_period and 'start_date' in eng.current_period.keys():
            period_start = eng.current_period['start_date']
        
        start_date = min_date or period_start
        end_date = max_date or datetime.now().date().isoformat()
        
        if not start_date:
            start_date = '1900-01-01'
        
        print(f"Date Range: {start_date} to {end_date}")
        
        # Get trial balance for income statement
        rows_is = db.compute_trial_balance(
            from_date=start_date,
            up_to_date=end_date,
            include_temporary=True,
            period_id=eng.current_period_id,
            exclude_closing=True,  # ignore closing entries so temporary accounts retain activity
            conn=eng.conn
        )
        
        print(f"Trial Balance Rows: {len(list(rows_is))}")
        
        revenue_found = []
        expense_found = []
        
        for row in rows_is:
            acc_type = (row['type'] if 'type' in row.keys() else '').lower()
            if acc_type == 'revenue':
                net_debit = float(row['net_debit'] if 'net_debit' in row.keys() else 0)
                net_credit = float(row['net_credit'] if 'net_credit' in row.keys() else 0)
                amount = net_credit - net_debit
                if abs(amount) > 0.01:
                    revenue_found.append((row['name'] if 'name' in row.keys() else 'Unknown', amount))
            elif acc_type == 'expense':
                net_debit = float(row['net_debit'] if 'net_debit' in row.keys() else 0)
                net_credit = float(row['net_credit'] if 'net_credit' in row.keys() else 0)
                amount = net_debit - net_credit
                if abs(amount) > 0.01:
                    expense_found.append((row['name'] if 'name' in row.keys() else 'Unknown', amount))
        
        print(f"\nRevenue Accounts in Trial Balance: {len(revenue_found)}")
        for name, amt in revenue_found:
            print(f"  {name}: {PESO_SYMBOL}{amt:,.2f}")
        
        print(f"\nExpense Accounts in Trial Balance: {len(expense_found)}")
        for name, amt in expense_found:
            print(f"  {name}: {PESO_SYMBOL}{amt:,.2f}")
        
        # Generate income statement using engine
        print("\n5. GENERATING INCOME STATEMENT (using engine)")
        print("-" * 80)
        income_stmt = eng.generate_income_statement(start_date, end_date)
        
        print(f"Total Revenue: {PESO_SYMBOL}{income_stmt.get('total_revenue', 0):,.2f}")
        print(f"Total Expenses: {PESO_SYMBOL}{income_stmt.get('total_expense', 0):,.2f}")
        print(f"Net Income: {PESO_SYMBOL}{income_stmt.get('net_income', 0):,.2f}")
        
        if income_stmt.get('total_revenue', 0) == 0 and income_stmt.get('total_expense', 0) == 0:
            print("\n✗ PROBLEM: Income statement shows zero!")
        else:
            print("\n✓ Income statement has values")
        
        print()
        
        # Test cash flow generation
        print("6. TESTING CASH FLOW GENERATION")
        print("-" * 80)
        
        cash_flow = eng.generate_cash_flow(start_date, end_date)
        
        if isinstance(cash_flow, dict) and cash_flow.get('error'):
            print(f"✗ ERROR: {cash_flow.get('error')}")
        else:
            sections = cash_flow.get('sections', {})
            totals = cash_flow.get('totals', {})
            
            print(f"Operating Activities: {len(sections.get('Operating', []))} items, Total: {PESO_SYMBOL}{totals.get('Operating', 0):,.2f}")
            print(f"Investing Activities: {len(sections.get('Investing', []))} items, Total: {PESO_SYMBOL}{totals.get('Investing', 0):,.2f}")
            print(f"Financing Activities: {len(sections.get('Financing', []))} items, Total: {PESO_SYMBOL}{totals.get('Financing', 0):,.2f}")
            print(f"Net Change in Cash: {PESO_SYMBOL}{cash_flow.get('net_change_in_cash', 0):,.2f}")
            
            if totals.get('Operating', 0) == 0 and totals.get('Investing', 0) == 0 and totals.get('Financing', 0) == 0:
                print("\n✗ PROBLEM: Cash flow shows zero!")
            else:
                print("\n✓ Cash flow has values")
        
        print()
        
        # Check Cash account
        print("7. CHECKING CASH ACCOUNT")
        print("-" * 80)
        cash_acc = db.get_account_by_name('Cash', eng.conn)
        if cash_acc:
            cash_id = cash_acc['id']
            cur = eng.conn.execute("""
                SELECT COALESCE(SUM(jl.debit), 0) as total_debit,
                       COALESCE(SUM(jl.credit), 0) as total_credit
                FROM journal_lines jl
                JOIN journal_entries je ON je.id = jl.entry_id
                WHERE jl.account_id = ?
                  AND je.period_id = ?
                  AND (je.status = 'posted' OR je.status IS NULL)
            """, (cash_id, eng.current_period_id))
            
            cash_result = cur.fetchone()
            cash_debit = float(cash_result['total_debit'] or 0)
            cash_credit = float(cash_result['total_credit'] or 0)
            cash_balance = cash_debit - cash_credit
            
            print(f"Cash Debits: {PESO_SYMBOL}{cash_debit:,.2f}")
            print(f"Cash Credits: {PESO_SYMBOL}{cash_credit:,.2f}")
            print(f"Cash Balance: {PESO_SYMBOL}{cash_balance:,.2f}")
            
            if cash_balance == 0:
                print("\n⚠ WARNING: Cash account has zero balance - cash flow will be zero")
        
        print()
        print("=" * 80)
        print("DIAGNOSTIC COMPLETE")
        print("=" * 80)
        print("\nRECOMMENDATIONS:")
        print("1. Make sure date range in Financial Statements tab includes your entry dates")
        print("2. Ensure all entries have status='posted'")
        print("3. Check that entries are in the current accounting period")
        print("4. Verify that revenue/expense accounts have activity")
        print("5. For cash flow, ensure Cash account has transactions")
        
    finally:
        eng.close()


if __name__ == '__main__':
    main()

