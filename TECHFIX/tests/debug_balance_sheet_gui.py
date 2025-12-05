"""
Debug script to check what the GUI balance sheet calculation would show
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from techfix import db
from techfix.accounting import AccountingEngine
from datetime import date, datetime

PESO_SYMBOL = "₱ "

def format_currency(amount):
    return f"{PESO_SYMBOL}{amount:,.2f}"

def main():
    eng = AccountingEngine()
    
    # Simulate what GUI does - get dates from Financial Statements tab
    # User said the GUI shows "As of 2025-12-06"
    date_from = None  # Could be set in GUI
    date_to = "2025-12-06"  # This is what GUI shows
    
    print("=" * 80)
    print("SIMULATING GUI BALANCE SHEET CALCULATION")
    print("=" * 80)
    print()
    print(f"Date From: {date_from or 'Not set'}")
    print(f"Date To: {date_to}")
    print()
    
    # Simulate the period filter logic from GUI
    if date_from and date_to:
        period_filter = None  # Cross-period reporting
    elif date_to:
        period_filter = None  # Include all entries up to date_to
    else:
        period_filter = eng.current_period_id  # Fallback to period filter
    
    print(f"Period Filter: {period_filter if period_filter else 'None (cross-period)'}")
    print()
    
    # Check if closing entries are completed
    statuses = eng.get_cycle_status()
    step8 = next((r for r in statuses if int(r['step']) == 8), None)
    closing_completed = step8 and (step8['status'] == 'completed')
    inc_temp_bs = not closing_completed
    
    print(f"Closing Entries Completed: {closing_completed}")
    print(f"Include Temporary Accounts: {inc_temp_bs}")
    print()
    
    # Get trial balance the way GUI does
    rows_bs = db.compute_trial_balance(
        up_to_date=date_to,
        include_temporary=inc_temp_bs,
        period_id=period_filter,
        conn=eng.conn
    )
    
    print(f"Trial Balance Rows: {len(list(rows_bs))}")
    print()
    
    # Now generate balance sheet the way GUI does
    # GUI calls: self.engine.generate_balance_sheet(as_of_date)
    # But generate_balance_sheet uses self.current_period_id, not period_filter!
    print("=" * 80)
    print("BALANCE SHEET USING GUI METHOD")
    print("=" * 80)
    print()
    
    balance_sheet = eng.generate_balance_sheet(date_to)
    
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
        print("This matches what you're seeing in the GUI!")
        print()
        print("The issue is that generate_balance_sheet() uses current_period_id")
        print("but the GUI might be trying to do cross-period reporting.")
    
    print()
    print("=" * 80)
    
    # Check what entries exist
    print()
    print("CHECKING ENTRIES:")
    print("=" * 80)
    
    # Check entries in current period
    cur = eng.conn.execute("""
        SELECT COUNT(*) as cnt, MIN(date) as min_date, MAX(date) as max_date
        FROM journal_entries 
        WHERE period_id = ? AND date <= date(?)
    """, (eng.current_period_id, date_to))
    result = cur.fetchone()
    print(f"Entries in current period (ID={eng.current_period_id}) up to {date_to}:")
    print(f"  Count: {result['cnt']}")
    print(f"  Date range: {result['min_date']} to {result['max_date']}")
    print()
    
    # Check entries in other periods
    cur = eng.conn.execute("""
        SELECT period_id, COUNT(*) as cnt, MIN(date) as min_date, MAX(date) as max_date
        FROM journal_entries 
        WHERE period_id != ? AND date <= date(?)
        GROUP BY period_id
    """, (eng.current_period_id, date_to))
    other_periods = cur.fetchall()
    if other_periods:
        print(f"Entries in OTHER periods up to {date_to}:")
        for row in other_periods:
            print(f"  Period ID {row['period_id']}: {row['cnt']} entries ({row['min_date']} to {row['max_date']})")
    else:
        print("No entries in other periods")

if __name__ == '__main__':
    main()

