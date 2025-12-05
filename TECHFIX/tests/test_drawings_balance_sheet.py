"""
Test that Owner's Drawings correctly reduces equity on balance sheet.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from techfix import db
from techfix.accounting import AccountingEngine
from techfix.accounting import JournalLine

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
    print("TEST: Owner's Drawings Balance Sheet Calculation")
    print("=" * 80)
    print()
    
    eng = AccountingEngine()
    
    try:
        if not eng.current_period_id:
            print("✗ ERROR: No active accounting period!")
            return
        
        # Get accounts
        capital_account = db.get_account_by_name("Owner's Capital", eng.conn)
        drawings_account = db.get_account_by_name("Owner's Drawings", eng.conn)
        cash_account = db.get_account_by_name("Cash", eng.conn)
        
        if not all([capital_account, drawings_account, cash_account]):
            print("✗ ERROR: Required accounts not found!")
            return
        
        print("Creating test transaction with Owner's Drawings...")
        print()
        
        # Create a test transaction: Owner withdraws ₱5,000
        # Debit: Owner's Drawings ₱5,000
        # Credit: Cash ₱5,000
        entry_id = eng.record_entry(
            date="2025-01-15",
            description="Test: Owner's withdrawal",
            lines=[
                JournalLine(account_id=drawings_account['id'], debit=5000.0),
                JournalLine(account_id=cash_account['id'], credit=5000.0),
            ],
            status="posted",
        )
        
        print(f"✓ Created test entry #{entry_id}")
        print()
        
        # Generate balance sheet
        balance_sheet = eng.generate_balance_sheet("2025-01-15")
        
        total_assets = float(balance_sheet.get('total_assets', 0))
        total_liabilities = float(balance_sheet.get('total_liabilities', 0))
        total_equity = float(balance_sheet.get('total_equity', 0))
        balance_check = float(balance_sheet.get('balance_check', 0))
        
        print("BALANCE SHEET RESULTS:")
        print("-" * 80)
        print(f"Total Assets:        {PESO_SYMBOL}{total_assets:,.2f}")
        print(f"Total Liabilities:   {PESO_SYMBOL}{total_liabilities:,.2f}")
        print(f"Total Equity:        {PESO_SYMBOL}{total_equity:,.2f}")
        print(f"Liabilities + Equity: {PESO_SYMBOL}{total_liabilities + total_equity:,.2f}")
        print(f"Balance Check:       {PESO_SYMBOL}{balance_check:,.2f}")
        print()
        
        # Check equity items
        print("EQUITY ITEMS:")
        print("-" * 80)
        for equity_item in balance_sheet.get('equity', []):
            name = equity_item.get('name', 'Unknown')
            amount = float(equity_item.get('amount', 0))
            print(f"  {name}: {PESO_SYMBOL}{amount:,.2f}")
        
        print()
        print("VERIFICATION:")
        print("-" * 80)
        
        # Check if Owner's Drawings is in the equity list
        drawings_in_equity = False
        drawings_amount_in_bs = 0.0
        capital_amount = 0.0
        
        for equity_item in balance_sheet.get('equity', []):
            name = equity_item.get('name', '').lower()
            amount = float(equity_item.get('amount', 0))
            
            if "drawing" in name:
                drawings_in_equity = True
                drawings_amount_in_bs = amount
            elif "capital" in name and "owner" in name:
                capital_amount = amount
        
        if drawings_in_equity:
            print(f"✓ Owner's Drawings found in equity: {PESO_SYMBOL}{drawings_amount_in_bs:,.2f}")
            if drawings_amount_in_bs > 0:
                print(f"  ⚠ WARNING: Drawings is POSITIVE - it should reduce equity")
                print(f"  Expected: Equity = Capital - Drawings")
                print(f"  Current calculation might be: Equity = Capital + Drawings (WRONG)")
            else:
                print(f"  ✓ Drawings is negative or zero (correct)")
        else:
            print("ℹ Owner's Drawings not shown separately (may be netted into Capital)")
        
        print()
        if abs(balance_check) < 0.01:
            print("✓ Balance sheet is BALANCED")
            print("  Owner's Drawings is being handled correctly")
        else:
            print("✗ Balance sheet is NOT BALANCED")
            print(f"  Difference: {PESO_SYMBOL}{abs(balance_check):,.2f}")
            print("  Owner's Drawings might be causing the imbalance")
        
        # Clean up - delete the test entry
        print()
        print("Cleaning up test entry...")
        eng.conn.execute("DELETE FROM journal_entries WHERE id = ?", (entry_id,))
        eng.conn.commit()
        print("✓ Test entry deleted")
        
    finally:
        eng.close()


if __name__ == '__main__':
    main()

