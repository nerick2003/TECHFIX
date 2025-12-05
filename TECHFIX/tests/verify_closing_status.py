"""
Verify if closing entries are actually completed in the GUI database
"""
import sys
import os
from pathlib import Path
import sqlite3

root_db = Path(r"C:\Users\neric\Desktop\FOR VIDEO\techfix.sqlite3")

if not root_db.exists():
    print(f"Database not found: {root_db}")
    sys.exit(1)

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from techfix.accounting import AccountingEngine

conn = sqlite3.connect(str(root_db))
conn.row_factory = sqlite3.Row

try:
    eng = AccountingEngine(conn=conn)
    
    print("=" * 80)
    print("CHECKING CLOSING ENTRIES STATUS")
    print("=" * 80)
    print()
    
    # Check cycle status
    statuses = eng.get_cycle_status()
    step8 = next((r for r in statuses if int(r['step']) == 8), None)
    
    if step8:
        print(f"Step 8 (Closing Entries) Status: {step8['status']}")
        note = step8['note'] if 'note' in step8.keys() else 'N/A'
        print(f"Note: {note}")
        print()
    else:
        print("Step 8 not found in cycle status")
        print()
    
    # Check if there are closing entries
    closing_count = conn.execute("""
        SELECT COUNT(*) as cnt FROM journal_entries 
        WHERE is_closing = 1 AND period_id = ?
    """, (eng.current_period_id,)).fetchone()
    
    print(f"Closing entries in database: {closing_count['cnt']}")
    print()
    
    # Check Owner's Capital balance
    capital_balance = conn.execute("""
        SELECT SUM(jl.credit) - SUM(jl.debit) as balance
        FROM journal_lines jl
        JOIN journal_entries je ON je.id = jl.entry_id
        JOIN accounts a ON a.id = jl.account_id
        WHERE a.name = "Owner's Capital"
          AND je.period_id = ?
          AND (je.status = 'posted' OR je.status IS NULL)
    """, (eng.current_period_id,)).fetchone()
    
    capital_bal = float(capital_balance['balance'] or 0)
    print(f"Owner's Capital Balance: ₱ {capital_bal:,.2f}")
    print()
    
    # Check if revenue/expense accounts have zero balances (should be zero after closing)
    revenue_balances = conn.execute("""
        SELECT a.name, SUM(jl.credit) - SUM(jl.debit) as balance
        FROM accounts a
        JOIN journal_lines jl ON jl.account_id = a.id
        JOIN journal_entries je ON je.id = jl.entry_id
        WHERE a.type = 'Revenue'
          AND je.period_id = ?
          AND (je.status = 'posted' OR je.status IS NULL)
        GROUP BY a.id, a.name
        HAVING ABS(SUM(jl.credit) - SUM(jl.debit)) > 0.005
    """, (eng.current_period_id,)).fetchall()
    
    expense_balances = conn.execute("""
        SELECT a.name, SUM(jl.debit) - SUM(jl.credit) as balance
        FROM accounts a
        JOIN journal_lines jl ON jl.account_id = a.id
        JOIN journal_entries je ON je.id = jl.entry_id
        WHERE a.type = 'Expense'
          AND je.period_id = ?
          AND (je.status = 'posted' OR je.status IS NULL)
        GROUP BY a.id, a.name
        HAVING ABS(SUM(jl.debit) - SUM(jl.credit)) > 0.005
    """, (eng.current_period_id,)).fetchall()
    
    print("Revenue accounts with non-zero balances (should be zero after closing):")
    if revenue_balances:
        for r in revenue_balances:
            print(f"  {r['name']}: ₱ {float(r['balance']):,.2f}")
    else:
        print("  ✓ All revenue accounts are zero")
    print()
    
    print("Expense accounts with non-zero balances (should be zero after closing):")
    if expense_balances:
        for e in expense_balances:
            print(f"  {e['name']}: ₱ {float(e['balance']):,.2f}")
    else:
        print("  ✓ All expense accounts are zero")
    print()
    
    if revenue_balances or expense_balances:
        print("⚠ WARNING: Revenue/Expense accounts are NOT zero!")
        print("This means closing entries did not close all temporary accounts.")
        print("The balance sheet calculation might be incorrect.")
    else:
        print("✓ All temporary accounts are closed correctly.")
        print("The balance sheet should use: Assets = Liabilities + Equity")
        print("(NOT Assets = Liabilities + Equity + Net Income)")
    
finally:
    conn.close()

