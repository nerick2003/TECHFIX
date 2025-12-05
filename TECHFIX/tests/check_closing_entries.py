"""
Check closing entries in the GUI database to see what was closed to Owner's Capital
"""
import sys
import os
from pathlib import Path
import sqlite3

root_db = Path(r"C:\Users\neric\Desktop\FOR VIDEO\techfix.sqlite3")

if not root_db.exists():
    print(f"Database not found: {root_db}")
    sys.exit(1)

conn = sqlite3.connect(str(root_db))
conn.row_factory = sqlite3.Row

try:
    # Get current period
    period = conn.execute("SELECT id, name FROM accounting_periods WHERE is_current = 1").fetchone()
    period_id = period['id']
    
    print("=" * 80)
    print("CHECKING CLOSING ENTRIES")
    print("=" * 80)
    print()
    print(f"Period: {period['name']} (ID: {period_id})")
    print()
    
    # Get all closing entries
    closing_entries = conn.execute("""
        SELECT je.id, je.date, je.description,
               SUM(CASE WHEN a.name = "Owner's Capital" THEN jl.credit - jl.debit ELSE 0 END) as capital_change
        FROM journal_entries je
        JOIN journal_lines jl ON jl.entry_id = je.id
        JOIN accounts a ON a.id = jl.account_id
        WHERE je.is_closing = 1
          AND je.period_id = ?
          AND (je.status = 'posted' OR je.status IS NULL)
        GROUP BY je.id
        ORDER BY je.date, je.id
    """, (period_id,)).fetchall()
    
    print(f"Closing Entries: {len(closing_entries)}")
    print()
    
    total_capital_added = 0.0
    for entry in closing_entries:
        capital_change = float(entry['capital_change'] or 0)
        total_capital_added += capital_change
        print(f"Entry #{entry['id']}: {entry['date']} - {entry['description']}")
        print(f"  Capital Change: ₱ {capital_change:,.2f}")
        print()
    
    print(f"Total Capital Added by Closing Entries: ₱ {total_capital_added:,.2f}")
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
    """, (period_id,)).fetchone()
    
    capital_bal = float(capital_balance['balance'] or 0)
    print(f"Owner's Capital Total Balance: ₱ {capital_bal:,.2f}")
    print()
    
    # Check revenue and expense totals that should have been closed
    revenue_total = conn.execute("""
        SELECT SUM(jl.credit) - SUM(jl.debit) as total
        FROM journal_lines jl
        JOIN journal_entries je ON je.id = jl.entry_id
        JOIN accounts a ON a.id = jl.account_id
        WHERE a.type = 'Revenue'
          AND je.period_id = ?
          AND (je.status = 'posted' OR je.status IS NULL)
          AND (je.is_closing = 0 OR je.is_closing IS NULL)
    """, (period_id,)).fetchone()
    
    expense_total = conn.execute("""
        SELECT SUM(jl.debit) - SUM(jl.credit) as total
        FROM journal_lines jl
        JOIN journal_entries je ON je.id = jl.entry_id
        JOIN accounts a ON a.id = jl.account_id
        WHERE a.type = 'Expense'
          AND je.period_id = ?
          AND (je.status = 'posted' OR je.status IS NULL)
          AND (je.is_closing = 0 OR je.is_closing IS NULL)
    """, (period_id,)).fetchone()
    
    rev_total = float(revenue_total['total'] or 0)
    exp_total = float(expense_total['total'] or 0)
    net_income = rev_total - exp_total
    
    print("Revenue/Expense Summary (before closing):")
    print(f"  Total Revenue: ₱ {rev_total:,.2f}")
    print(f"  Total Expenses: ₱ {exp_total:,.2f}")
    print(f"  Net Income: ₱ {net_income:,.2f}")
    print()
    print(f"Expected Capital Increase: ₱ {net_income:,.2f}")
    print(f"Actual Capital Added: ₱ {total_capital_added:,.2f}")
    print(f"Difference: ₱ {abs(net_income - total_capital_added):,.2f}")
    print()
    
    # Check assets
    assets_total = conn.execute("""
        SELECT SUM(CASE 
            WHEN a.type = 'Asset' THEN jl.debit - jl.credit
            WHEN a.type = 'Contra-Asset' THEN -(jl.credit - jl.debit)
            ELSE 0
        END) as total
        FROM journal_lines jl
        JOIN journal_entries je ON je.id = jl.entry_id
        JOIN accounts a ON a.id = jl.account_id
        WHERE (a.type = 'Asset' OR a.type = 'Contra-Asset')
          AND je.period_id = ?
          AND (je.status = 'posted' OR je.status IS NULL)
    """, (period_id,)).fetchone()
    
    assets_bal = float(assets_total['total'] or 0)
    print(f"Total Assets: ₱ {assets_bal:,.2f}")
    print()
    
    print("=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    print()
    print(f"Assets: ₱ {assets_bal:,.2f}")
    print(f"Owner's Capital: ₱ {capital_bal:,.2f}")
    print(f"Difference: ₱ {abs(assets_bal - capital_bal):,.2f}")
    print()
    
    if abs(assets_bal - capital_bal) > 0.05:
        print("⚠ The imbalance suggests:")
        print("  1. Owner's Capital includes net income from closing entries")
        print("  2. But Assets don't reflect all the transactions")
        print("  3. This could mean:")
        print("     - Some asset transactions are missing")
        print("     - Closing entries calculated incorrectly")
        print("     - Revenue/expenses were closed but assets weren't recorded")
    
finally:
    conn.close()

