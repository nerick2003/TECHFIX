"""
Fix script to correct adjusting entries that incorrectly credit Supplies account.

This script is a command-line wrapper for AccountingEngine.fix_supplies_account_entries()
"""

import sys
import os
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


def fix_supplies_account_entries(dry_run: bool = True):
    """
    Fix adjusting entries that incorrectly credit Supplies account.
    
    Args:
        dry_run: If True, only show what would be fixed without making changes
    """
    print("=" * 80)
    print("FIX SUPPLIES ACCOUNT ENTRIES")
    print("=" * 80)
    print()
    
    if dry_run:
        print("⚠️  DRY RUN MODE - No changes will be made")
        print()
    
    eng = AccountingEngine()
    
    try:
        if not eng.current_period_id:
            print("ERROR: No active accounting period!")
            return
        
        # Get diagnosis first to show details
        diagnosis = eng.diagnose_supplies_account_issue()
        
        if diagnosis.get('error'):
            print(f"ERROR: {diagnosis['error']}")
            return
        
        if not diagnosis.get('has_issue') or not diagnosis.get('problematic_entries'):
            print("✓ No problematic entries found. Supplies account is fine.")
            return
        
        problematic_entries = diagnosis['problematic_entries']
        print(f"Found {len(problematic_entries)} problematic entries:")
        print()
        
        # Show details of entries to be fixed
        for entry_info in problematic_entries:
            print(f"  Entry ID {entry_info['entry_id']}: {entry_info['description']}")
            print(f"    Date: {entry_info['date']}, Reference: {entry_info['document_ref'] or '(none)'}")
            print(f"    Currently credits: Supplies ({PESO_SYMBOL}{entry_info['credit_amount']:,.2f})")
            print(f"    Should credit: {entry_info['should_credit']}")
            print()
        
        # Call the fix method
        result = eng.fix_supplies_account_entries(dry_run=dry_run)
        
        if result.get('error'):
            print(f"ERROR: {result['error']}")
            return
        
        # Show results
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print()
        print(result['message'])
        
        if result.get('fixed_entries'):
            print()
            print("Fixed entries:")
            for old_id, new_id in result['fixed_entries'].items():
                if new_id:
                    print(f"  Entry {old_id} → recreated as entry {new_id}")
                else:
                    print(f"  Entry {old_id} (would be fixed in execute mode)")
        
        if result.get('errors'):
            print()
            print("ERRORS:")
            for error_info in result['errors']:
                print(f"  Entry {error_info['entry_id']}: {error_info['error']}")
        
        if not dry_run and result['fixed_count'] > 0:
            print()
            print("✓ Changes committed to database")
            print()
            print("Next steps:")
            print("1. Run diagnose_balance_sheet.py again to verify the fix")
            print("2. Check that Supplies account balance is now correct")
        
    finally:
        eng.close()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Fix Supplies account entries')
    parser.add_argument('--execute', action='store_true', 
                       help='Actually make the changes (default is dry-run)')
    args = parser.parse_args()
    
    fix_supplies_account_entries(dry_run=not args.execute)

