"""
Check all entries in GUI database to understand the imbalance
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
    period = conn.execute("SELECT id, name FROM accounting_periods WHERE is_current = 1").fetchone()
    period_id = period['id']
    
    print("=" * 80)
    print("ALL ENTRIES IN GUI DATABASE")
    print("=" * 80)
    print()
    
    # Get all entries
    entries = conn.execute("""
        SELECT je.id, je.date, je.description, je.status, je.is_closing,
               SUM(jl.debit) as total_debit, SUM(jl.credit) as total_credit
        FROM journal_entries je
        JOIN journal_lines jl ON jl.entry_id = je.id
        WHERE je.period_id = ?
          AND (je.status = 'posted' OR je.status IS NULL)
        GROUP BY je.id
        ORDER BY je.date, je.id
    """, (period_id,)).fetchall()
    
    print(f"Total entries: {len(entries)}")
    print()
    
    for entry in entries:
        closing = " [CLOSING]" if entry['is_closing'] else ""
        print(f"Entry #{entry['id']}: {entry['date']} - {entry['description']}{closing}")
        print(f"  Debit: ₱ {float(entry['total_debit'] or 0):,.2f}, Credit: ₱ {float(entry['total_credit'] or 0):,.2f}")
    print()
    
    # Check balance sheet as of different dates
    print("=" * 80)
    print("BALANCE SHEET AS OF DIFFERENT DATES")
    print("=" * 80)
    print()
    
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    from techfix.accounting import AccountingEngine
    
    eng = AccountingEngine(conn=conn)
    
    dates_to_check = ["2025-12-05", "2025-12-06", "2025-12-31"]
    
    for as_of_date in dates_to_check:
        balance_sheet = eng.generate_balance_sheet(as_of_date)
        
        assets = balance_sheet.get('assets', [])
        liabilities = balance_sheet.get('liabilities', [])
        equity = balance_sheet.get('equity', [])
        
        total_assets = sum(a.get('amount', 0) for a in assets)
        total_liabilities = sum(l.get('amount', 0) for l in liabilities)
        total_equity = sum(e.get('amount', 0) for e in equity)
        
        balance_check = total_assets - (total_liabilities + total_equity)
        
        print(f"As of {as_of_date}:")
        print(f"  Assets: ₱ {total_assets:,.2f}")
        print(f"  Liabilities: ₱ {total_liabilities:,.2f}")
        print(f"  Equity: ₱ {total_equity:,.2f}")
        print(f"  Balance Check: ₱ {abs(balance_check):,.2f} {'✅' if abs(balance_check) < 0.05 else '❌'}")
        print()
    
finally:
    conn.close()

