"""
Check and fix balance sheet imbalance by examining actual account balances.
"""

import sys
import os
import sqlite3
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from techfix import db
from techfix.accounting import AccountingEngine

PESO_SYMBOL = "₱ "
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
    print("BALANCE SHEET IMBALANCE FIX CHECKER")
    print("=" * 80)
    print()
    
    eng = AccountingEngine()
    
    try:
        if not eng.current_period_id:
            print("✗ ERROR: No active accounting period!")
            return
        
        # Get the date
        cur = eng.conn.execute("""
            SELECT MAX(date) as max_date
            FROM journal_entries
            WHERE period_id = ?
              AND (status = 'posted' OR status IS NULL)
        """, (eng.current_period_id,))
        
        result = cur.fetchone()
        as_of_date = result['max_date'] if result and result['max_date'] else '2025-12-31'
        
        print(f"Checking balance sheet as of: {as_of_date}")
        print()
        
        # Generate balance sheet
        balance_sheet = eng.generate_balance_sheet(as_of_date)
        
        total_assets = float(balance_sheet.get('total_assets', 0))
        total_liabilities = float(balance_sheet.get('total_liabilities', 0))
        total_equity = float(balance_sheet.get('total_equity', 0))
        balance_check = float(balance_sheet.get('balance_check', 0))
        
        print("BALANCE SHEET TOTALS:")
        print("-" * 80)
        print(f"Total Assets:        {PESO_SYMBOL}{total_assets:,.2f}")
        print(f"Total Liabilities:   {PESO_SYMBOL}{total_liabilities:,.2f}")
        print(f"Total Equity:        {PESO_SYMBOL}{total_equity:,.2f}")
        print(f"Liabilities + Equity: {PESO_SYMBOL}{total_liabilities + total_equity:,.2f}")
        print(f"Balance Check:       {PESO_SYMBOL}{balance_check:,.2f}")
        print()
        
        if abs(balance_check) < 0.01:
            print("✓ Balance sheet is BALANCED")
            print()
            print("If the GUI still shows an imbalance:")
            print("1. Close and restart the application")
            print("2. Go to Financial Statements tab")
            print("3. Click 'Generate' or 'Refresh' button")
            return
        else:
            print("✗ Balance sheet is NOT BALANCED")
            print(f"  Difference: {PESO_SYMBOL}{abs(balance_check):,.2f}")
            print()
        
        # Check each equity account in detail
        print("DETAILED EQUITY ACCOUNT ANALYSIS:")
        print("-" * 80)
        
        rows = db.compute_trial_balance(
            up_to_date=as_of_date,
            include_temporary=False,
            period_id=eng.current_period_id,
            conn=eng.conn,
        )
        
        for r in rows:
            acc_type = (r["type"] or "").lower()
            if acc_type == "equity":
                name = r["name"]
                net_debit = float(r["net_debit"] or 0.0)
                net_credit = float(r["net_credit"] or 0.0)
                balance = net_credit - net_debit
                
                print(f"\n{name}:")
                print(f"  Debits:  {PESO_SYMBOL}{net_debit:,.2f}")
                print(f"  Credits: {PESO_SYMBOL}{net_credit:,.2f}")
                print(f"  Balance (Credit - Debit): {PESO_SYMBOL}{balance:,.2f}")
                
                if "drawing" in name.lower():
                    drawings_amount = net_debit - net_credit
                    print(f"  Drawings Amount (Debit - Credit): {PESO_SYMBOL}{drawings_amount:,.2f}")
                    if drawings_amount > 0:
                        print(f"  ✓ Drawings has debit balance (correct)")
                        print(f"  Expected: Equity should be REDUCED by {PESO_SYMBOL}{drawings_amount:,.2f}")
                    elif drawings_amount < 0:
                        print(f"  ⚠ WARNING: Drawings has CREDIT balance (unusual)")
                        print(f"  This might indicate an error in the data")
                    else:
                        print(f"  ✓ Drawings balance is zero")
        
        print()
        print("RECOMMENDATIONS:")
        print("-" * 80)
        print("1. Make sure you've RESTARTED the application after the code fix")
        print("2. Check if closing entries have been made properly")
        print("3. Verify that Owner's Drawings transactions are correct")
        print("4. If the imbalance persists, check for:")
        print("   - Revenue/Expense accounts not closed to Capital")
        print("   - Incorrect journal entries")
        print("   - Missing or duplicate transactions")
        
    finally:
        eng.close()


if __name__ == '__main__':
    main()

