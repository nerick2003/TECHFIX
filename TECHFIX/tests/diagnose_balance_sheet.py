"""
Comprehensive diagnostic tool to identify why the balance sheet doesn't balance.
This will check each step of the accounting cycle and identify where the imbalance occurs.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Fix Windows console encoding for peso symbol
PESO_SYMBOL = "PHP "  # Use PHP instead of peso symbol to avoid encoding issues on Windows
try:
    if sys.platform == 'win32':
        # Try to set UTF-8 encoding for Windows console
        import io
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        PESO_SYMBOL = "₱ "  # Try peso symbol if encoding works
except Exception:
    PESO_SYMBOL = "PHP "  # Fallback to PHP if encoding fails

from techfix import db
from techfix.accounting import AccountingEngine

def diagnose_balance_sheet():
    """Diagnose why the balance sheet doesn't balance."""
    print("=" * 80)
    print("BALANCE SHEET DIAGNOSTIC TOOL")
    print("=" * 80)
    print()
    
    eng = AccountingEngine()
    
    try:
        if not eng.current_period_id:
            print("ERROR: No active accounting period!")
            return
        
        print(f"Current Period ID: {eng.current_period_id}")
        print()
        
        # Step 1: Check Trial Balance
        print("=" * 80)
        print("STEP 1: TRIAL BALANCE CHECK")
        print("=" * 80)
        print()
        
        rows = db.compute_trial_balance(
            period_id=eng.current_period_id,
            include_temporary=True,
            conn=eng.conn
        )
        
        total_debits = sum(float(r['net_debit'] or 0) for r in rows)
        total_credits = sum(float(r['net_credit'] or 0) for r in rows)
        diff = abs(total_debits - total_credits)
        
        print(f"Total Debits:  {PESO_SYMBOL}{total_debits:,.2f}")
        print(f"Total Credits: {PESO_SYMBOL}{total_credits:,.2f}")
        print(f"Difference:    {PESO_SYMBOL}{diff:,.2f}")
        
        if diff < 0.01:
            print("✓ Trial Balance is BALANCED")
        else:
            print("✗ Trial Balance is NOT BALANCED")
            print()
            print("ISSUE FOUND: Trial balance doesn't balance!")
            print("This means there are unbalanced journal entries.")
            print("Check your journal entries - each entry must have equal debits and credits.")
            return
        
        print()
        
        # Step 2: Check Post-Closing Trial Balance
        print("=" * 80)
        print("STEP 2: POST-CLOSING TRIAL BALANCE CHECK")
        print("=" * 80)
        print()
        
        rows_pc = db.compute_trial_balance(
            period_id=eng.current_period_id,
            include_temporary=False,
            conn=eng.conn
        )
        
        total_debits_pc = sum(float(r['net_debit'] or 0) for r in rows_pc)
        total_credits_pc = sum(float(r['net_credit'] or 0) for r in rows_pc)
        diff_pc = abs(total_debits_pc - total_credits_pc)
        
        print(f"Total Debits:  {PESO_SYMBOL}{total_debits_pc:,.2f}")
        print(f"Total Credits: {PESO_SYMBOL}{total_credits_pc:,.2f}")
        print(f"Difference:    {PESO_SYMBOL}{diff_pc:,.2f}")
        
        if diff_pc < 0.01:
            print("✓ Post-Closing Trial Balance is BALANCED")
        else:
            print("✗ Post-Closing Trial Balance is NOT BALANCED")
            print()
            print("ISSUE FOUND: Post-closing trial balance doesn't balance!")
            print("This means closing entries created an imbalance.")
            print("Check your closing entries - they may have errors.")
        
        print()
        
        # Step 3: Check Account Balances
        print("=" * 80)
        print("STEP 3: ACCOUNT BALANCE ANALYSIS")
        print("=" * 80)
        print()
        
        # Check for accounts with unusual balances
        unusual_balances = []
        for r in rows_pc:
            acc_type = (r['type'] or '').lower()
            normal_side = (r['normal_side'] or '').lower()
            net_debit = float(r['net_debit'] or 0)
            net_credit = float(r['net_credit'] or 0)
            balance = net_debit - net_credit
            
            # Check if balance is opposite of normal side
            if acc_type == 'asset' and normal_side == 'debit' and balance < 0:
                unusual_balances.append((r['name'], 'Asset with credit balance', balance, r['name']))
            elif acc_type == 'liability' and normal_side == 'credit' and balance > 0:
                unusual_balances.append((r['name'], 'Liability with debit balance', balance, r['name']))
            elif acc_type == 'equity' and normal_side == 'credit' and balance > 0:
                unusual_balances.append((r['name'], 'Equity with debit balance', balance, r['name']))
        
        if unusual_balances:
            print("⚠️  UNUSUAL ACCOUNT BALANCES (opposite of normal side):")
            for name, issue, bal, acc_name in unusual_balances:
                print(f"   - {name}: {issue} ({PESO_SYMBOL}{bal:,.2f})")
                
                # Special check for Supplies account - use the inline diagnostic method
                if acc_name == 'Supplies' and bal < 0:
                    print()
                    print("   ⚠️  SUPPLIES ACCOUNT ISSUE DETECTED:")
                    print("      This usually means an adjusting entry credited Supplies,")
                    print("      but Supplies had no debit balance because purchases were")
                    print("      recorded to 'Supplies Expense' instead.")
                    print()
                    
                    # Use the inline diagnostic method
                    supplies_diagnosis = eng.diagnose_supplies_account_issue()
                    if supplies_diagnosis.get('has_issue') and supplies_diagnosis.get('problematic_entries'):
                        print("      PROBLEMATIC ENTRIES FOUND:")
                        print("      These adjusting entries incorrectly credited Supplies account!")
                        print()
                        for entry in supplies_diagnosis['problematic_entries']:
                            print(f"      - Entry ID {entry['entry_id']}: {entry['description']}")
                            print(f"        Date: {entry['date']}, Reference: {entry['document_ref'] or '(none)'}")
                            print(f"        Currently credits: Supplies ({PESO_SYMBOL}{entry['credit_amount']:,.2f})")
                            print(f"        Should credit: {entry.get('should_credit', 'Unknown account')}")
                        print()
                        print("      SOLUTION:")
                        print("      You can fix this automatically using the fix script, or manually:")
                        print()
                        print("      AUTOMATIC FIX (Recommended):")
                        print("      Run: python TECHFIX/TECHFIX/tests/fix_supplies_account_entries.py")
                        print("      Then: python TECHFIX/TECHFIX/tests/fix_supplies_account_entries.py --execute")
                        print()
                        print("      MANUAL FIX:")
                        print("      1. Go to Journal tab in TechFix")
                        print("      2. For each entry listed above:")
                        print("         a. Delete the incorrect entry")
                        print("         b. Re-enter it with the CORRECT credit account shown above")
                        print("      3. Example: Entry 17 should credit 'Accumulated Depreciation',")
                        print("         not 'Supplies'")
                        print()
                        print("      INLINE FIX CODE (copy and run in Python):")
                        print("      " + "=" * 76)
                        print("      import sys, os")
                        print("      sys.path.insert(0, os.path.abspath('TECHFIX/TECHFIX'))")
                        print("      from techfix.accounting import AccountingEngine")
                        print()
                        print("      eng = AccountingEngine()")
                        print("      # Dry run first to see what would be fixed")
                        print("      result = eng.fix_supplies_account_entries(dry_run=True)")
                        print("      print(result['message'])")
                        print()
                        print("      # Then execute the fix")
                        print("      result = eng.fix_supplies_account_entries(dry_run=False)")
                        print("      print(result['message'])")
                        print("      eng.close()")
                        print("      " + "=" * 76)
                    else:
                        print("      SOLUTION:")
                        print("      1. Find the adjusting entry that credited Supplies")
                        print("      2. Delete that adjusting entry")
                        print("      3. If supplies are expensed immediately (not stored),")
                        print("         no adjusting entry is needed")
                    print()
            print()
        else:
            print("✓ All account balances are normal")
            print()
        
        # Step 4: Generate Balance Sheet and Check
        print("=" * 80)
        print("STEP 4: BALANCE SHEET CALCULATION")
        print("=" * 80)
        print()
        
        # Initialize variable for revenue/expense check
        revenue_expense_in_bs = []
        
        # Get the date for balance sheet
        cur = eng.conn.execute("""
            SELECT MAX(date) as max_date FROM journal_entries 
            WHERE period_id = ?
        """, (eng.current_period_id,))
        max_date = cur.fetchone()['max_date'] or '2025-12-31'
        
        balance_sheet = eng.generate_balance_sheet(max_date)
        
        # Initialize variable for revenue/expense check (used in summary)
        revenue_expense_in_bs = []
        
        print(f"Balance Sheet as of: {max_date}")
        print()
        print(f"Total Assets:        {PESO_SYMBOL}{balance_sheet['total_assets']:,.2f}")
        print(f"Total Liabilities:    {PESO_SYMBOL}{balance_sheet['total_liabilities']:,.2f}")
        print(f"Total Equity:         {PESO_SYMBOL}{balance_sheet['total_equity']:,.2f}")
        print(f"Balance Check:        {PESO_SYMBOL}{balance_sheet['balance_check']:,.2f}")
        print()
        
        # Check for revenue/expense accounts in permanent accounts (always check, not just when unbalanced)
        for r in rows_pc:
            acc_type = (r['type'] or '').lower()
            if acc_type in ('revenue', 'expense'):
                net_debit = float(r['net_debit'] or 0)
                net_credit = float(r['net_credit'] or 0)
                if abs(net_debit - net_credit) > 0.01:
                    revenue_expense_in_bs.append((r['name'], net_debit - net_credit))
        
        if abs(balance_sheet['balance_check']) < 0.01:
            print("✓ Balance Sheet is BALANCED")
        else:
            print("✗ Balance Sheet is NOT BALANCED")
            print()
            print("DETAILED BREAKDOWN:")
            print()
            
            # Show assets
            print("ASSETS:")
            for asset in balance_sheet['assets']:
                print(f"  {asset['name']}: {PESO_SYMBOL}{asset['amount']:,.2f}")
            print()
            
            # Show liabilities
            print("LIABILITIES:")
            if balance_sheet['liabilities']:
                for liab in balance_sheet['liabilities']:
                    print(f"  {liab['name']}: {PESO_SYMBOL}{liab['amount']:,.2f}")
            else:
                print("  (none)")
            print()
            
            # Show equity
            print("EQUITY:")
            for eq in balance_sheet['equity']:
                print(f"  {eq['name']}: {PESO_SYMBOL}{eq['amount']:,.2f}")
            print()
            
            # Check for missing accounts
            print("CHECKING FOR ISSUES:")
            print()
            
            # Check if Owner's Capital is too high (might include unclosed revenue)
            capital_accounts = [e for e in balance_sheet['equity'] if 'Capital' in e['name']]
            if capital_accounts:
                capital_amt = capital_accounts[0]['amount']
                if capital_amt > 50000:  # Suspiciously high
                    print(f"⚠️  Owner's Capital is very high ({PESO_SYMBOL}{capital_amt:,.2f})")
                    print("   This might indicate unclosed revenue/expense accounts are included.")
                    print()
            
            if revenue_expense_in_bs:
                print("⚠️  REVENUE/EXPENSE ACCOUNTS FOUND IN PERMANENT ACCOUNTS:")
                print("   These should have been closed to equity!")
                for name, bal in revenue_expense_in_bs:
                    print(f"   - {name}: {PESO_SYMBOL}{bal:,.2f}")
                print()
                print("SOLUTION: Make sure closing entries were posted correctly.")
                print()
        
        # Step 5: Check Closing Entries
        print("=" * 80)
        print("STEP 5: CLOSING ENTRIES CHECK")
        print("=" * 80)
        print()
        
        cur = eng.conn.execute("""
            SELECT COUNT(*) as count FROM journal_entries 
            WHERE period_id = ? AND is_closing = 1
        """, (eng.current_period_id,))
        closing_count = cur.fetchone()['count']
        
        print(f"Closing entries found: {closing_count}")
        
        # Check cycle status
        statuses = eng.get_cycle_status()
        step8 = next((r for r in statuses if int(r['step']) == 8), None)
        if step8:
            print(f"Step 8 (Closing Entries) status: {step8['status']}")
            if step8['status'] != 'completed':
                print("⚠️  WARNING: Closing entries step is not marked as completed!")
                print("   This might cause temporary accounts to be included in balance sheet.")
        
        print()
        
        # Step 6: Check for Reversing Entries Issues
        print("=" * 80)
        print("STEP 6: REVERSING ENTRIES CHECK")
        print("=" * 80)
        print()
        
        cur = eng.conn.execute("""
            SELECT COUNT(*) as count FROM journal_entries 
            WHERE period_id = ? AND is_reversing = 1
        """, (eng.current_period_id,))
        reversing_count = cur.fetchone()['count']
        
        print(f"Reversing entries found: {reversing_count}")
        
        # Check if reversing entries are balanced
        cur = eng.conn.execute("""
            SELECT je.id, je.description,
                   SUM(jl.debit) as total_debit,
                   SUM(jl.credit) as total_credit
            FROM journal_entries je
            JOIN journal_lines jl ON jl.entry_id = je.id
            WHERE je.period_id = ? AND je.is_reversing = 1
            GROUP BY je.id
            HAVING ABS(SUM(jl.debit) - SUM(jl.credit)) > 0.01
        """, (eng.current_period_id,))
        
        unbalanced_reversing = cur.fetchall()
        if unbalanced_reversing:
            print("⚠️  UNBALANCED REVERSING ENTRIES FOUND:")
            for entry in unbalanced_reversing:
                print(f"   Entry {entry['id']}: {entry['description']}")
                print(f"      Debit: {PESO_SYMBOL}{entry['total_debit']:,.2f}, Credit: {PESO_SYMBOL}{entry['total_credit']:,.2f}")
            print()
        else:
            print("✓ All reversing entries are balanced")
        
        print()
        
        # Summary
        print("=" * 80)
        print("SUMMARY & RECOMMENDATIONS")
        print("=" * 80)
        print()
        
        issues = []
        if diff >= 0.01:
            issues.append("Trial balance doesn't balance")
        if diff_pc >= 0.01:
            issues.append("Post-closing trial balance doesn't balance")
        if abs(balance_sheet['balance_check']) >= 0.01:
            issues.append("Balance sheet doesn't balance")
        if revenue_expense_in_bs:
            issues.append("Revenue/expense accounts not closed")
        if unbalanced_reversing:
            issues.append("Unbalanced reversing entries")
        
        if not issues:
            print("✓ No issues found! Balance sheet should balance correctly.")
        else:
            print("⚠️  ISSUES FOUND:")
            for i, issue in enumerate(issues, 1):
                print(f"   {i}. {issue}")
            print()
            print("RECOMMENDED FIXES:")
            print("1. Verify all journal entries have equal debits and credits")
            print("2. Ensure closing entries were posted correctly")
            print("3. Check that revenue/expense accounts are closed to equity")
            print("4. Verify reversing entries are balanced")
            print("5. Make sure balance sheet only includes permanent accounts")
        
    finally:
        eng.close()

if __name__ == '__main__':
    diagnose_balance_sheet()

