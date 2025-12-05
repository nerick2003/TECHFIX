"""
Diagnose the specific balance sheet imbalance: Assets 44,086.39 vs Liab+Equity 50,009.45
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
    print("DIAGNOSING SPECIFIC BALANCE SHEET IMBALANCE")
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
        
        print("CURRENT BALANCE SHEET:")
        print("-" * 80)
        print(f"Total Assets:        {PESO_SYMBOL}{total_assets:,.2f}")
        print(f"Total Liabilities:   {PESO_SYMBOL}{total_liabilities:,.2f}")
        print(f"Total Equity:        {PESO_SYMBOL}{total_equity:,.2f}")
        print(f"Liabilities + Equity: {PESO_SYMBOL}{total_liabilities + total_equity:,.2f}")
        print(f"Balance Check:       {PESO_SYMBOL}{balance_check:,.2f}")
        print()
        
        # Check if this matches the error
        if abs(total_assets - 44086.39) < 0.01:
            print("✓ MATCHES ERROR: Assets = ₱44,086.39")
        if abs((total_liabilities + total_equity) - 50009.45) < 0.01:
            print("✓ MATCHES ERROR: Liabilities + Equity = ₱50,009.45")
        if abs(balance_check - 5923.06) < 0.01:
            print("✓ MATCHES ERROR: Difference = ₱5,923.06")
        print()
        
        # Detailed breakdown
        print("DETAILED EQUITY BREAKDOWN:")
        print("-" * 80)
        
        equity_sum = 0.0
        for equity_item in balance_sheet.get('equity', []):
            name = equity_item.get('name', 'Unknown')
            amount = float(equity_item.get('amount', 0))
            equity_sum += amount
            print(f"  {name}: {PESO_SYMBOL}{amount:,.2f}")
        
        print(f"\n  Sum of equity items: {PESO_SYMBOL}{equity_sum:,.2f}")
        print(f"  Reported total equity: {PESO_SYMBOL}{total_equity:,.2f}")
        print(f"  Difference: {PESO_SYMBOL}{abs(equity_sum - total_equity):,.2f}")
        print()
        
        # Check trial balance for equity accounts
        print("TRIAL BALANCE - EQUITY ACCOUNTS:")
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
                
                print(f"{name}:")
                print(f"  Debits:  {PESO_SYMBOL}{net_debit:,.2f}")
                print(f"  Credits: {PESO_SYMBOL}{net_credit:,.2f}")
                print(f"  Balance: {PESO_SYMBOL}{balance:,.2f}")
                
                # Check if this is Owner's Drawings
                if "drawing" in name.lower():
                    if balance > 0:
                        print(f"  ⚠ ISSUE: Drawings has CREDIT balance (should be DEBIT)")
                        print(f"    This means drawings are being treated as increasing equity!")
                    else:
                        print(f"  ✓ Drawings has debit balance (correct)")
                print()
        
        # Check if revenue/expense accounts are in permanent accounts
        print("CHECKING FOR REVENUE/EXPENSE IN BALANCE SHEET:")
        print("-" * 80)
        
        revenue_expense_found = []
        for r in rows:
            acc_type = (r["type"] or "").lower()
            if acc_type in ("revenue", "expense"):
                name = r["name"]
                net_debit = float(r["net_debit"] or 0.0)
                net_credit = float(r["net_credit"] or 0.0)
                balance = abs(net_debit - net_credit)
                if balance > 0.01:
                    revenue_expense_found.append((name, acc_type, balance))
        
        if revenue_expense_found:
            print("✗ PROBLEM: Revenue/Expense accounts found in balance sheet!")
            print("  These should be closed to Owner's Capital, not shown separately.")
            for name, acc_type, bal in revenue_expense_found:
                print(f"  {name} ({acc_type}): {PESO_SYMBOL}{bal:,.2f}")
        else:
            print("✓ No revenue/expense accounts in balance sheet")
        
        print()
        print("RECOMMENDATION:")
        print("-" * 80)
        
        if abs(balance_check - 5923.06) < 0.01:
            print("The imbalance of ₱5,923.06 suggests:")
            print("1. Owner's Drawings might be added instead of subtracted")
            print("2. Revenue/Expense accounts might not be closed properly")
            print("3. There might be a calculation error in equity")
            print()
            print("ACTION: Check if closing entries were made properly")
        
    finally:
        eng.close()


if __name__ == '__main__':
    main()

