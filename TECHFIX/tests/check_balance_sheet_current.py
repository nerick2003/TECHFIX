"""
Quick script to check current balance sheet status
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
    
    print("=" * 80)
    print("CURRENT BALANCE SHEET STATUS")
    print("=" * 80)
    print()
    
    # Get current period info
    period = eng.current_period
    period_id = eng.current_period_id
    period_name = period['name'] if period and 'name' in period.keys() else 'N/A'
    print(f"Current Period: {period_name}")
    print(f"Period ID: {period_id}")
    print()
    
    # Check if closing entries are completed
    statuses = eng.get_cycle_status()
    step8 = next((r for r in statuses if int(r['step']) == 8), None)
    closing_completed = step8 and (step8['status'] == 'completed')
    print(f"Closing Entries Status: {'COMPLETED' if closing_completed else 'NOT COMPLETED'}")
    print()
    
    # Get latest date
    cur = eng.conn.execute("""
        SELECT MAX(date) as max_date FROM journal_entries 
        WHERE period_id = ?
    """, (period_id,))
    result = cur.fetchone()
    as_of_date = result['max_date'] if result and result['max_date'] else date.today().isoformat()
    
    print(f"Balance Sheet as of: {as_of_date}")
    print()
    
    # Generate balance sheet
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
    
    # Get Net Income if period is open
    net_income = 0.0
    if not closing_completed:
        try:
            period_start = period['start_date'] if period and 'start_date' in period.keys() else None
            if period_start:
                income_stmt = eng.generate_income_statement(period_start, as_of_date, period_id=None)
                net_income = income_stmt.get('net_income', 0.0)
        except Exception as e:
            print(f"Could not calculate Net Income: {e}")
    
    # Balance Check
    print("=" * 80)
    print("BALANCE CHECK")
    print("=" * 80)
    
    if closing_completed:
        # After closing: Assets = Liabilities + Equity
        balance_check = total_assets - (total_liabilities + total_equity)
        print(f"Equation: Assets = Liabilities + Equity")
        print(f"  {format_currency(total_assets)} = {format_currency(total_liabilities)} + {format_currency(total_equity)}")
        print(f"  {format_currency(total_assets)} = {format_currency(total_liabilities + total_equity)}")
    else:
        # Before closing: Assets = Liabilities + Equity + Net Income
        balance_check = total_assets - (total_liabilities + total_equity + net_income)
        print(f"Equation: Assets = Liabilities + Equity + Net Income")
        print(f"  {format_currency(total_assets)} = {format_currency(total_liabilities)} + {format_currency(total_equity)} + {format_currency(net_income)}")
        print(f"  {format_currency(total_assets)} = {format_currency(total_liabilities + total_equity + net_income)}")
        print()
        print(f"Net Income: {format_currency(net_income)}")
    
    print()
    print(f"Difference: {format_currency(abs(balance_check))}")
    
    if abs(balance_check) < 0.05:
        print()
        print("✓ BALANCE SHEET IS BALANCED ✅")
    else:
        print()
        print("✗ BALANCE SHEET IS NOT BALANCED ❌")
        print()
        print("Possible issues:")
        print("  1. Check for unbalanced journal entries")
        print("  2. Verify closing entries were created correctly")
        print("  3. Check for draft entries that weren't posted")
        print("  4. Review account balances in Trial Balance tab")
    
    print()
    print("=" * 80)

if __name__ == '__main__':
    main()

