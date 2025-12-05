"""
Check the balance sheet from the GUI database as of 2025-12-06
"""
import sys
import os
from pathlib import Path
import sqlite3

# Use the root database (where GUI runs from)
root_db = Path(r"C:\Users\neric\Desktop\FOR VIDEO\techfix.sqlite3")

if not root_db.exists():
    print(f"Database not found: {root_db}")
    sys.exit(1)

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from techfix import db
from techfix.accounting import AccountingEngine

conn = sqlite3.connect(str(root_db))
conn.row_factory = sqlite3.Row

try:
    eng = AccountingEngine(conn=conn)
    
    as_of_date = "2025-12-06"
    
    print("=" * 80)
    print(f"BALANCE SHEET FROM GUI DATABASE AS OF {as_of_date}")
    print("=" * 80)
    print()
    print(f"Database: {root_db}")
    print()
    
    # Check current period
    current_period = eng.current_period
    print(f"Current Period: {current_period['name']} (ID: {eng.current_period_id})")
    print()
    
    # Generate balance sheet
    balance_sheet = eng.generate_balance_sheet(as_of_date)
    
    assets = balance_sheet.get('assets', [])
    liabilities = balance_sheet.get('liabilities', [])
    equity = balance_sheet.get('equity', [])
    
    total_assets = sum(a.get('amount', 0) for a in assets)
    total_liabilities = sum(l.get('amount', 0) for l in liabilities)
    total_equity = sum(e.get('amount', 0) for e in equity)
    
    print("ASSETS:")
    for asset in assets:
        amount = asset.get('amount', 0)
        if abs(amount) > 0.005:
            print(f"  {asset.get('name'):<40} ₱ {amount:>12,.2f}")
    print(f"  {'Total Assets':<40} ₱ {total_assets:>12,.2f}")
    print()
    
    print("LIABILITIES:")
    for liab in liabilities:
        amount = liab.get('amount', 0)
        if abs(amount) > 0.005:
            print(f"  {liab.get('name'):<40} ₱ {amount:>12,.2f}")
    if not liabilities or total_liabilities == 0:
        print("  (none)")
    print(f"  {'Total Liabilities':<40} ₱ {total_liabilities:>12,.2f}")
    print()
    
    print("EQUITY:")
    for eq in equity:
        amount = eq.get('amount', 0)
        if abs(amount) > 0.005:
            print(f"  {eq.get('name'):<40} ₱ {amount:>12,.2f}")
    print(f"  {'Total Equity':<40} ₱ {total_equity:>12,.2f}")
    print()
    
    balance_check = total_assets - (total_liabilities + total_equity)
    print("=" * 80)
    print("BALANCE CHECK")
    print("=" * 80)
    print(f"Assets:                    ₱ {total_assets:>12,.2f}")
    print(f"Liabilities + Equity:      ₱ {total_liabilities + total_equity:>12,.2f}")
    print(f"Difference:                ₱ {abs(balance_check):>12,.2f} {'✅' if abs(balance_check) < 0.05 else '❌'}")
    print()
    
    if abs(balance_check) > 0.05:
        print("⚠ IMBALANCED!")
        print()
        print("This matches what you're seeing in the GUI.")
        print()
        print("Possible causes:")
        print("  1. Missing asset entries")
        print("  2. Incorrect equity entries")
        print("  3. Entries not posted")
        print("  4. Date filter excluding some entries")
        print()
        print("Let's check entries up to this date...")
        print()
        
        # Check entries up to this date
        entries = conn.execute("""
            SELECT je.id, je.date, je.description, je.status,
                   SUM(jl.debit) as total_debit, SUM(jl.credit) as total_credit
            FROM journal_entries je
            JOIN journal_lines jl ON jl.entry_id = je.id
            WHERE date(je.date) <= date(?)
              AND je.period_id = ?
              AND (je.status = 'posted' OR je.status IS NULL)
            GROUP BY je.id
            ORDER BY je.date, je.id
        """, (as_of_date, eng.current_period_id)).fetchall()
        
        print(f"Entries up to {as_of_date}: {len(entries)}")
        print()
        print("Recent entries (last 10):")
        for entry in entries[-10:]:
            debit = float(entry['total_debit'] or 0)
            credit = float(entry['total_credit'] or 0)
            balanced = "✅" if abs(debit - credit) < 0.01 else "❌"
            print(f"  Entry #{entry['id']}: {entry['date']} - {entry['description']} {balanced}")
            if abs(debit - credit) > 0.01:
                print(f"    UNBALANCED! Debit: ₱ {debit:,.2f}, Credit: ₱ {credit:,.2f}")
        
        # Check for unbalanced entries
        unbalanced = [e for e in entries if abs(float(e['total_debit'] or 0) - float(e['total_credit'] or 0)) > 0.01]
        if unbalanced:
            print()
            print(f"⚠ Found {len(unbalanced)} unbalanced entries!")
            for e in unbalanced:
                print(f"  Entry #{e['id']}: {e['date']} - {e['description']}")
                print(f"    Debit: ₱ {float(e['total_debit'] or 0):,.2f}, Credit: ₱ {float(e['total_credit'] or 0):,.2f}")
    
finally:
    conn.close()

