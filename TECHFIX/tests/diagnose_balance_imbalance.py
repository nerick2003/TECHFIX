"""
Diagnose the specific balance sheet imbalance shown in the GUI.
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
    print("BALANCE SHEET IMBALANCE DIAGNOSTIC")
    print("=" * 80)
    print()
    
    eng = AccountingEngine()
    
    try:
        if not eng.current_period_id:
            print("✗ ERROR: No active accounting period!")
            return
        
        # Get the date range
        cur = eng.conn.execute("""
            SELECT MIN(date) as min_date, MAX(date) as max_date
            FROM journal_entries
            WHERE period_id = ?
              AND (status = 'posted' OR status IS NULL)
        """, (eng.current_period_id,))
        
        date_range = cur.fetchone()
        as_of_date = date_range['max_date'] or '2025-12-31'
        
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
        
        # Check if this matches the error
        if abs(total_assets - 44086.39) < 0.01:
            print("⚠ MATCHES ERROR: Assets = ₱44,086.39")
        if abs((total_liabilities + total_equity) - 50009.45) < 0.01:
            print("⚠ MATCHES ERROR: Liabilities + Equity = ₱50,009.45")
        if abs(balance_check - 5923.06) < 0.01:
            print("⚠ MATCHES ERROR: Difference = ₱5,923.06")
        
        print()
        print("DETAILED BREAKDOWN:")
        print("-" * 80)
        
        # Check each equity account
        print("EQUITY ACCOUNTS:")
        for equity_item in balance_sheet.get('equity', []):
            name = equity_item.get('name', 'Unknown')
            amount = float(equity_item.get('amount', 0))
            print(f"  {name}: {PESO_SYMBOL}{amount:,.2f}")
            
            # Check if this is Owner's Drawings
            if "drawing" in name.lower():
                print(f"    ⚠ This is Owner's Drawings - should REDUCE equity")
                print(f"    Current calculation: {'ADDING' if amount > 0 else 'SUBTRACTING'}")
        
        print()
        print("CHECKING FOR ISSUES:")
        print("-" * 80)
        
        # Check if Owner's Drawings is being added instead of subtracted
        drawings_found = False
        drawings_amount = 0.0
        capital_amount = 0.0
        
        for equity_item in balance_sheet.get('equity', []):
            name = equity_item.get('name', '').lower()
            amount = float(equity_item.get('amount', 0))
            
            if "drawing" in name:
                drawings_found = True
                drawings_amount = amount
                if amount > 0:
                    print(f"✗ PROBLEM: Owner's Drawings shows as POSITIVE ({PESO_SYMBOL}{amount:,.2f})")
                    print(f"  Drawings should REDUCE equity, not increase it.")
                    print(f"  If drawings is being added to equity, that's wrong.")
            elif "capital" in name and "owner" in name:
                capital_amount = amount
        
        if drawings_found and drawings_amount > 0:
            print()
            print("CALCULATION CHECK:")
            print(f"  Owner's Capital: {PESO_SYMBOL}{capital_amount:,.2f}")
            print(f"  Owner's Drawings: {PESO_SYMBOL}{drawings_amount:,.2f}")
            print(f"  Current Total Equity: {PESO_SYMBOL}{total_equity:,.2f}")
            print()
            print(f"  If drawings is being ADDED:")
            print(f"    Equity = Capital + Drawings = {PESO_SYMBOL}{capital_amount + drawings_amount:,.2f} ❌ WRONG")
            print()
            print(f"  If drawings is being SUBTRACTED:")
            print(f"    Equity = Capital - Drawings = {PESO_SYMBOL}{capital_amount - drawings_amount:,.2f} ✓ CORRECT")
        
        # Check trial balance for Owner's Drawings
        print()
        print("TRIAL BALANCE CHECK FOR OWNER'S DRAWINGS:")
        print("-" * 80)
        
        drawings_account = db.get_account_by_name("Owner's Drawings", eng.conn)
        if drawings_account:
            cur = eng.conn.execute("""
                SELECT 
                    COALESCE(SUM(jl.debit), 0) as total_debit,
                    COALESCE(SUM(jl.credit), 0) as total_credit,
                    COALESCE(SUM(jl.debit), 0) - COALESCE(SUM(jl.credit), 0) as balance
                FROM journal_lines jl
                JOIN journal_entries je ON je.id = jl.entry_id
                WHERE jl.account_id = ?
                  AND je.period_id = ?
                  AND (je.status = 'posted' OR je.status IS NULL)
            """, (drawings_account['id'], eng.current_period_id))
            
            result = cur.fetchone()
            if result:
                drawings_debit = float(result['total_debit'] or 0)
                drawings_credit = float(result['total_credit'] or 0)
                drawings_balance = float(result['balance'] or 0)
                
                print(f"Owner's Drawings Account:")
                print(f"  Total Debits:  {PESO_SYMBOL}{drawings_debit:,.2f}")
                print(f"  Total Credits: {PESO_SYMBOL}{drawings_credit:,.2f}")
                print(f"  Net Balance:   {PESO_SYMBOL}{drawings_balance:,.2f}")
                print()
                print(f"  Expected: Debit balance (positive) = drawings reduce equity")
                print(f"  On balance sheet, this should be SUBTRACTED from Capital")
        
        print()
        print("RECOMMENDATION:")
        print("-" * 80)
        if abs(balance_check) > 0.01:
            print("✗ Balance sheet is NOT balanced")
            print("  Check if Owner's Drawings is being added instead of subtracted")
            print("  Verify that all equity accounts are calculated correctly")
        else:
            print("✓ Balance sheet is balanced")
            print("  If GUI shows different values, check date range or period filter")
        
    finally:
        eng.close()


if __name__ == '__main__':
    main()

