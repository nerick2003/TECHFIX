"""
Check balance sheet equity calculation for consistency issues.
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
    print("BALANCE SHEET EQUITY CONSISTENCY CHECK")
    print("=" * 80)
    print()
    
    eng = AccountingEngine()
    
    try:
        if not eng.current_period_id:
            print("✗ ERROR: No active accounting period!")
            return
        
        # Get all equity accounts
        print("EQUITY ACCOUNTS DETAIL:")
        print("-" * 80)
        
        rows = db.compute_trial_balance(
            up_to_date="2025-12-31",
            include_temporary=False,
            period_id=eng.current_period_id,
            conn=eng.conn,
        )
        
        owner_capital = 0.0
        owner_drawings = 0.0
        net_income_from_closing = 0.0
        
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
                print()
                
                if "capital" in name.lower() and "owner" in name.lower():
                    owner_capital = balance
                elif "drawing" in name.lower() or "withdrawal" in name.lower():
                    owner_drawings = balance  # This will be negative (debit balance)
        
        # Check closing entries to see net income
        print("CLOSING ENTRIES ANALYSIS:")
        print("-" * 80)
        
        cur = eng.conn.execute("""
            SELECT je.id, je.date, je.description, jl.account_id, a.name as account_name,
                   jl.debit, jl.credit
            FROM journal_entries je
            JOIN journal_lines jl ON jl.entry_id = je.id
            JOIN accounts a ON a.id = jl.account_id
            WHERE je.is_closing = 1
              AND je.period_id = ?
              AND (je.status = 'posted' OR je.status IS NULL)
            ORDER BY je.id, jl.id
        """, (eng.current_period_id,))
        
        closing_entries = cur.fetchall()
        capital_closing_debits = 0.0
        capital_closing_credits = 0.0
        
        for entry in closing_entries:
            if "Owner's Capital" in entry['account_name']:
                capital_closing_debits += float(entry['debit'] or 0)
                capital_closing_credits += float(entry['credit'] or 0)
        
        net_income_from_closing = capital_closing_credits - capital_closing_debits
        
        print(f"Closing entries affecting Owner's Capital:")
        print(f"  Total Debits to Capital:  {PESO_SYMBOL}{capital_closing_debits:,.2f}")
        print(f"  Total Credits to Capital: {PESO_SYMBOL}{capital_closing_credits:,.2f}")
        print(f"  Net Income (Credits - Debits): {PESO_SYMBOL}{net_income_from_closing:,.2f}")
        print()
        
        # Calculate what equity should be
        print("EQUITY CALCULATION:")
        print("-" * 80)
        print(f"Owner's Capital (after closing): {PESO_SYMBOL}{owner_capital:,.2f}")
        print(f"Owner's Drawings: {PESO_SYMBOL}{owner_drawings:,.2f}")
        print()
        
        # Owner's Drawings should REDUCE equity, not be added
        # If drawings has a debit balance (positive), it reduces equity
        # If drawings has a credit balance (negative), it increases equity (unusual)
        if owner_drawings > 0:
            print("⚠ WARNING: Owner's Drawings has a DEBIT balance (positive)")
            print("  This means drawings reduce equity, which is correct.")
            print(f"  Equity should be: Capital - Drawings = {PESO_SYMBOL}{owner_capital - owner_drawings:,.2f}")
        elif owner_drawings < 0:
            print("⚠ WARNING: Owner's Drawings has a CREDIT balance (negative)")
            print("  This is unusual - drawings should have debit balances.")
            print(f"  Equity should be: Capital - Drawings = {PESO_SYMBOL}{owner_capital - abs(owner_drawings):,.2f}")
        else:
            print("✓ Owner's Drawings balance is zero")
        
        # Check how balance sheet calculates equity
        print()
        print("BALANCE SHEET EQUITY CALCULATION:")
        print("-" * 80)
        balance_sheet = eng.generate_balance_sheet("2025-12-31")
        
        total_equity_reported = balance_sheet['total_equity']
        print(f"Balance Sheet Total Equity: {PESO_SYMBOL}{total_equity_reported:,.2f}")
        print()
        print("Equity line items:")
        for equity_item in balance_sheet.get('equity', []):
            name = equity_item['name']
            amount = float(equity_item['amount'])
            print(f"  {name}: {PESO_SYMBOL}{amount:,.2f}")
        
        print()
        print("ISSUE IDENTIFICATION:")
        print("-" * 80)
        
        # The issue: Owner's Drawings should REDUCE equity, not be added
        # If balance sheet shows Owner's Drawings as a positive amount being added,
        # that's wrong. It should be subtracted.
        
        drawings_in_equity = False
        drawings_amount = 0.0
        for equity_item in balance_sheet.get('equity', []):
            name = equity_item['name'].lower()
            if "drawing" in name or "withdrawal" in name:
                drawings_in_equity = True
                drawings_amount = float(equity_item['amount'])
                break
        
        if drawings_in_equity:
            if drawings_amount > 0:
                print("✗ PROBLEM: Owner's Drawings is shown as a POSITIVE amount in equity")
                print("  Drawings should REDUCE equity, not increase it.")
                print("  The balance sheet is adding drawings instead of subtracting them.")
                print()
                print("  Expected calculation:")
                print(f"    Owner's Capital: {PESO_SYMBOL}{owner_capital:,.2f}")
                print(f"    Less: Drawings:   {PESO_SYMBOL}{drawings_amount:,.2f}")
                print(f"    Total Equity:      {PESO_SYMBOL}{owner_capital - drawings_amount:,.2f}")
                print()
                print(f"  But balance sheet shows: {PESO_SYMBOL}{total_equity_reported:,.2f}")
            else:
                print("✓ Owner's Drawings is shown as negative (correct)")
        else:
            print("ℹ Owner's Drawings not shown separately in equity (may be netted into Capital)")
        
        # Check if balance sheet balances
        print()
        print("BALANCE CHECK:")
        print("-" * 80)
        total_assets = balance_sheet['total_assets']
        total_liabilities = balance_sheet['total_liabilities']
        balance_check = balance_sheet['balance_check']
        
        print(f"Total Assets:      {PESO_SYMBOL}{total_assets:,.2f}")
        print(f"Total Liabilities: {PESO_SYMBOL}{total_liabilities:,.2f}")
        print(f"Total Equity:      {PESO_SYMBOL}{total_equity_reported:,.2f}")
        print(f"Balance Check:     {PESO_SYMBOL}{balance_check:,.2f}")
        
        if abs(balance_check) < 0.01:
            print("✓ Balance sheet equation balances")
        else:
            print("✗ Balance sheet equation does NOT balance")
            print(f"  Expected: Assets = Liabilities + Equity")
            print(f"  Actual:   {PESO_SYMBOL}{total_assets:,.2f} ≠ {PESO_SYMBOL}{total_liabilities + total_equity_reported:,.2f}")
        
    finally:
        eng.close()


if __name__ == '__main__':
    main()

