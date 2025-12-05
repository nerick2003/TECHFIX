"""
Check balance sheet as of a specific date to match GUI
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from techfix import db
from techfix.accounting import AccountingEngine
from datetime import date

PESO_SYMBOL = "₱ "

def format_currency(amount):
    return f"{PESO_SYMBOL}{amount:,.2f}"

def main():
    eng = AccountingEngine()
    
    # Check balance sheet as of the date shown in GUI
    as_of_date = "2025-12-06"
    
    print("=" * 80)
    print(f"BALANCE SHEET AS OF {as_of_date}")
    print("=" * 80)
    print()
    
    # Generate balance sheet using the same method as GUI
    balance_sheet = eng.generate_balance_sheet(as_of_date)
    
    # Assets
    print("ASSETS:")
    assets = balance_sheet.get('assets', [])
    total_assets = 0.0
    for asset in assets:
        amount = float(asset.get('amount', 0))
        if abs(amount) > 0.005:
            print(f"  {asset.get('name', 'Unknown'):<40} {format_currency(amount)}")
            total_assets += amount
    print(f"  {'Total Assets':<40} {format_currency(total_assets)}")
    print()
    
    # Liabilities
    print("LIABILITIES:")
    liabilities = balance_sheet.get('liabilities', [])
    total_liabilities = 0.0
    for liab in liabilities:
        amount = float(liab.get('amount', 0))
        if abs(amount) > 0.005:
            print(f"  {liab.get('name', 'Unknown'):<40} {format_currency(amount)}")
            total_liabilities += amount
    if not liabilities or total_liabilities == 0:
        print("  (none)")
    print(f"  {'Total Liabilities':<40} {format_currency(total_liabilities)}")
    print()
    
    # Equity
    print("EQUITY:")
    equity = balance_sheet.get('equity', [])
    total_equity = 0.0
    for eq in equity:
        amount = float(eq.get('amount', 0))
        if abs(amount) > 0.005:
            print(f"  {eq.get('name', 'Unknown'):<40} {format_currency(amount)}")
            total_equity += amount
    print(f"  {'Total Equity':<40} {format_currency(total_equity)}")
    print()
    
    # Balance Check
    print("=" * 80)
    print("BALANCE CHECK")
    print("=" * 80)
    balance_check = total_assets - (total_liabilities + total_equity)
    print(f"Equation: Assets = Liabilities + Equity")
    print(f"  {format_currency(total_assets)} = {format_currency(total_liabilities)} + {format_currency(total_equity)}")
    print(f"  {format_currency(total_assets)} = {format_currency(total_liabilities + total_equity)}")
    print()
    print(f"Difference: {format_currency(abs(balance_check))}")
    
    if abs(balance_check) < 0.05:
        print()
        print("✓ BALANCED ✅")
    else:
        print()
        print("✗ NOT BALANCED ❌")
    
    print()
    print("=" * 80)
    print()
    
    # Check what entries exist up to this date
    print("CHECKING ENTRIES UP TO THIS DATE:")
    print("=" * 80)
    cur = eng.conn.execute("""
        SELECT COUNT(*) as cnt, 
               MIN(date) as min_date, 
               MAX(date) as max_date,
               SUM(CASE WHEN status = 'posted' THEN 1 ELSE 0 END) as posted_count,
               SUM(CASE WHEN status = 'draft' THEN 1 ELSE 0 END) as draft_count
        FROM journal_entries 
        WHERE period_id = ? AND date <= date(?)
    """, (eng.current_period_id, as_of_date))
    result = cur.fetchone()
    print(f"Total entries up to {as_of_date}: {result['cnt']}")
    print(f"Posted entries: {result['posted_count']}")
    print(f"Draft entries: {result['draft_count']}")
    print(f"Date range: {result['min_date']} to {result['max_date']}")
    print()
    
    # Check entries after this date
    cur = eng.conn.execute("""
        SELECT COUNT(*) as cnt, MIN(date) as min_date, MAX(date) as max_date
        FROM journal_entries 
        WHERE period_id = ? AND date > date(?)
    """, (eng.current_period_id, as_of_date))
    result = cur.fetchone()
    if result['cnt'] > 0:
        print(f"⚠ WARNING: There are {result['cnt']} entries AFTER {as_of_date}")
        print(f"  Date range: {result['min_date']} to {result['max_date']}")
        print(f"  These entries are NOT included in the balance sheet!")
    else:
        print(f"✓ No entries after {as_of_date}")

if __name__ == '__main__':
    main()

