"""
Verification script to compare actual database entries with expected values from DATA_SUMMARY.txt
This will help identify missing transactions, incorrect amounts, or account name mismatches.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from techfix import db
from techfix.accounting import AccountingEngine
from datetime import datetime

# Expected account balances from DATA_SUMMARY.txt
EXPECTED_BALANCES = {
    "Cash": {"debit": 26831.82, "credit": 16769.55, "net": 10062.27},
    "Accounts Receivable": {"debit": 7828.61, "credit": 4641.12, "net": 3187.49},
    "Office Equipment": {"debit": 3083.52, "credit": 0.0, "net": 3083.52},
    "Accumulated Depreciation": {"debit": 0.0, "credit": 641.00, "net": -641.00},
    "Accounts Payable": {"debit": 1360.92, "credit": 1869.46, "net": -508.54},
    "Utilities Payable": {"debit": 0.0, "credit": 148.74, "net": -148.74},
    "SSS, PhilHealth, and Pag-Ibig Payable": {"debit": 0.0, "credit": 317.24, "net": -317.24},
    "Accrued Percentage Tax Payable": {"debit": 0.0, "credit": 255.76, "net": -255.76},
    "Owner's Capital": {"debit": 0.0, "credit": 10711.72, "net": -10711.72},
    "Owner's Drawings": {"debit": 1543.45, "credit": 0.0, "net": 1543.45},
    "Service Income": {"debit": 0.0, "credit": 19307.59, "net": -19307.59},
    "Rent Expense": {"debit": 4643.51, "credit": 0.0, "net": 4643.51},
    "Utilities Expense": {"debit": 427.38, "credit": 0.0, "net": 427.38},
    "Salaries & Wages": {"debit": 5634.84, "credit": 0.0, "net": 5634.84},
    "Supplies Expense": {"debit": 2411.37, "credit": 0.0, "net": 2411.37},
    "Depreciation Expense": {"debit": 641.00, "credit": 0.0, "net": 641.00},
    "Percentage Tax Expense": {"debit": 255.76, "credit": 0.0, "net": 255.76},
}

# Expected transaction references
EXPECTED_REFERENCES = [
    "BAN-10000", "INV-10001", "BAN-10002", "INV-10003", "REC-10004",
    "REC-10005", "BAN-10006", "PAY-10007", "INV-10008", "REC-10009",
    "INV-10010", "REC-10011", "BAN-10012", "INV-10013", "BAN-10014",
    "BAN-10015", "ADJ-10016", "ADJ-10017", "ADJ-10018", "ADJ-10019"
]

def verify_transactions():
    """Verify all transactions match expected values."""
    print("=" * 80)
    print("TRANSACTION VERIFICATION REPORT")
    print("=" * 80)
    print()
    
    eng = AccountingEngine()
    
    try:
        # Get all journal entries
        cur = eng.conn.execute("""
            SELECT je.id, je.date, je.description, je.document_ref, je.external_ref,
                   je.is_adjusting, je.status,
                   COUNT(jl.id) as line_count
            FROM journal_entries je
            LEFT JOIN journal_lines jl ON jl.entry_id = je.id
            WHERE je.period_id = ?
            GROUP BY je.id
            ORDER BY je.date, je.id
        """, (eng.current_period_id,))
        entries = cur.fetchall()
        
        print(f"Found {len(entries)} journal entries in database")
        print()
        
        # Check for missing references
        found_refs = {e['document_ref'] for e in entries if e['document_ref']}
        missing_refs = set(EXPECTED_REFERENCES) - found_refs
        extra_refs = found_refs - set(EXPECTED_REFERENCES)
        
        if missing_refs:
            print("⚠️  MISSING TRANSACTIONS (Expected but not found):")
            for ref in sorted(missing_refs):
                print(f"   - {ref}")
            print()
        
        if extra_refs:
            print("ℹ️  EXTRA TRANSACTIONS (Found but not in expected list):")
            for ref in sorted(extra_refs):
                print(f"   - {ref}")
            print()
        
        # Verify trial balance
        print("=" * 80)
        print("TRIAL BALANCE VERIFICATION")
        print("=" * 80)
        print()
        
        rows = db.compute_trial_balance(
            period_id=eng.current_period_id,
            conn=eng.conn
        )
        
        total_debits = sum(float(r['net_debit'] or 0) for r in rows)
        total_credits = sum(float(r['net_credit'] or 0) for r in rows)
        
        print(f"Total Debits:  ₱ {total_debits:,.2f}")
        print(f"Total Credits: ₱ {total_credits:,.2f}")
        print(f"Difference:    ₱ {abs(total_debits - total_credits):,.2f}")
        
        if abs(total_debits - total_credits) < 0.01:
            print("✓ Trial Balance is BALANCED")
        else:
            print("✗ Trial Balance is NOT BALANCED")
        print()
        
        # Verify account balances
        print("=" * 80)
        print("ACCOUNT BALANCE VERIFICATION")
        print("=" * 80)
        print()
        
        account_map = {}
        for r in rows:
            account_map[r['name']] = {
                'debit': float(r['net_debit'] or 0),
                'credit': float(r['net_credit'] or 0),
                'net': float(r['net_debit'] or 0) - float(r['net_credit'] or 0)
            }
        
        mismatches = []
        missing_accounts = []
        
        for account_name, expected in EXPECTED_BALANCES.items():
            if account_name not in account_map:
                missing_accounts.append(account_name)
                print(f"✗ {account_name}: NOT FOUND IN DATABASE")
                print(f"    Expected: Debit ₱ {expected['debit']:,.2f}, Credit ₱ {expected['credit']:,.2f}, Net ₱ {expected['net']:,.2f}")
                print()
            else:
                actual = account_map[account_name]
                # Check if balances match (allow small rounding differences)
                debit_diff = abs(actual['debit'] - expected['debit'])
                credit_diff = abs(actual['credit'] - expected['credit'])
                net_diff = abs(actual['net'] - expected['net'])
                
                if debit_diff > 0.01 or credit_diff > 0.01 or net_diff > 0.01:
                    mismatches.append({
                        'account': account_name,
                        'expected': expected,
                        'actual': actual,
                        'differences': {
                            'debit': debit_diff,
                            'credit': credit_diff,
                            'net': net_diff
                        }
                    })
                    print(f"⚠️  {account_name}: MISMATCH")
                    print(f"    Expected: Debit ₱ {expected['debit']:,.2f}, Credit ₱ {expected['credit']:,.2f}, Net ₱ {expected['net']:,.2f}")
                    print(f"    Actual:   Debit ₱ {actual['debit']:,.2f}, Credit ₱ {actual['credit']:,.2f}, Net ₱ {actual['net']:,.2f}")
                    print(f"    Difference: Debit ₱ {debit_diff:,.2f}, Credit ₱ {credit_diff:,.2f}, Net ₱ {net_diff:,.2f}")
                    print()
                else:
                    print(f"✓ {account_name}: OK")
        
        # Check for accounts in database but not in expected list
        unexpected_accounts = set(account_map.keys()) - set(EXPECTED_BALANCES.keys())
        if unexpected_accounts:
            print()
            print("ℹ️  ACCOUNTS IN DATABASE BUT NOT IN EXPECTED LIST:")
            for acc in sorted(unexpected_accounts):
                bal = account_map[acc]
                if abs(bal['net']) > 0.01:  # Only show if has balance
                    print(f"   - {acc}: Net ₱ {bal['net']:,.2f}")
            print()
        
        # Financial Statements Verification
        print("=" * 80)
        print("FINANCIAL STATEMENTS VERIFICATION")
        print("=" * 80)
        print()
        
        # Income Statement
        income_stmt = eng.generate_income_statement("2025-12-01", "2025-12-31")
        print("INCOME STATEMENT:")
        print(f"  Total Revenue:  ₱ {income_stmt['total_revenue']:,.2f} (Expected: ₱ 19,307.59)")
        print(f"  Total Expenses: ₱ {income_stmt['total_expense']:,.2f} (Expected: ₱ 14,013.86)")
        print(f"  Net Income:     ₱ {income_stmt['net_income']:,.2f} (Expected: ₱ 5,293.73)")
        print()
        
        # Balance Sheet
        balance_sheet = eng.generate_balance_sheet("2025-12-31")
        print("BALANCE SHEET:")
        print(f"  Total Assets:        ₱ {balance_sheet['total_assets']:,.2f} (Expected: ₱ 15,692.28)")
        print(f"  Total Liabilities:    ₱ {balance_sheet['total_liabilities']:,.2f} (Expected: ₱ 1,230.28)")
        print(f"  Total Equity:         ₱ {balance_sheet['total_equity']:,.2f} (Expected: ₱ 14,462.00)")
        print(f"  Balance Check:        ₱ {balance_sheet['balance_check']:,.2f} (Should be 0.00)")
        
        if abs(balance_sheet['balance_check']) < 0.01:
            print("  ✓ Balance Sheet is BALANCED")
        else:
            print("  ✗ Balance Sheet is NOT BALANCED")
        print()
        
        # Summary
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print()
        
        if not missing_refs and not mismatches and not missing_accounts:
            print("✓ ALL CHECKS PASSED - Everything matches expected values!")
        else:
            print("⚠️  ISSUES FOUND:")
            if missing_refs:
                print(f"   - {len(missing_refs)} missing transaction(s)")
            if missing_accounts:
                print(f"   - {len(missing_accounts)} missing account(s)")
            if mismatches:
                print(f"   - {len(mismatches)} account balance mismatch(es)")
            print()
            print("RECOMMENDATIONS:")
            print("1. Check if all transactions were entered correctly")
            print("2. Verify account names match exactly (case-sensitive)")
            print("3. Ensure adjusting entries are marked as 'adjusting'")
            print("4. Check for duplicate or missing entries")
            print("5. Verify amounts were entered correctly")
        
    finally:
        eng.close()

if __name__ == '__main__':
    verify_transactions()

