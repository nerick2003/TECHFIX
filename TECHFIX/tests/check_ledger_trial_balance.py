"""
Diagnostic script to check why ledger and trial balance are blank
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from techfix import db
from techfix.accounting import AccountingEngine

def check_ledger_trial_balance():
    """Check why ledger and trial balance might be blank"""
    print("=" * 80)
    print("LEDGER AND TRIAL BALANCE DIAGNOSTIC")
    print("=" * 80)
    print()
    
    eng = AccountingEngine()
    
    try:
        if not eng.current_period_id:
            print("ERROR: No active accounting period!")
            return
        
        print(f"Current Period ID: {eng.current_period_id}")
        print()
        
        # Check journal entries
        print("=" * 80)
        print("JOURNAL ENTRIES CHECK")
        print("=" * 80)
        print()
        
        cur = eng.conn.execute("""
            SELECT id, date, description, status, period_id, is_adjusting, is_closing, is_reversing
            FROM journal_entries 
            WHERE period_id = ?
            ORDER BY date, id
        """, (eng.current_period_id,))
        entries = cur.fetchall()
        
        print(f"Total journal entries in period {eng.current_period_id}: {len(entries)}")
        print()
        
        if len(entries) == 0:
            print("⚠️  NO JOURNAL ENTRIES FOUND IN CURRENT PERIOD!")
            print()
            # Check if entries exist in other periods
            cur = eng.conn.execute("SELECT COUNT(*) as count FROM journal_entries")
            total = cur.fetchone()['count']
            print(f"Total journal entries in database: {total}")
            if total > 0:
                cur = eng.conn.execute("SELECT DISTINCT period_id FROM journal_entries")
                periods = [r['period_id'] for r in cur.fetchall()]
                print(f"Entries exist in periods: {periods}")
                print("SOLUTION: Make sure you're in the correct accounting period.")
            return
        
        # Show sample entries
        print("Sample entries:")
        for entry in entries[:5]:
            print(f"  ID: {entry['id']}, Date: {entry['date']}, Desc: {entry['description']}")
            print(f"      Status: {entry['status']}, Adjusting: {entry['is_adjusting']}, Closing: {entry['is_closing']}, Reversing: {entry['is_reversing']}")
        print()
        
        # Check entry statuses
        cur = eng.conn.execute("""
            SELECT status, COUNT(*) as count
            FROM journal_entries 
            WHERE period_id = ?
            GROUP BY status
        """, (eng.current_period_id,))
        statuses = cur.fetchall()
        print("Entry statuses:")
        for s in statuses:
            print(f"  {s['status'] or '(NULL)'}: {s['count']}")
        print()
        
        # Check journal lines
        print("=" * 80)
        print("JOURNAL LINES CHECK")
        print("=" * 80)
        print()
        
        cur = eng.conn.execute("""
            SELECT COUNT(*) as count
            FROM journal_lines jl
            JOIN journal_entries je ON jl.entry_id = je.id
            WHERE je.period_id = ?
        """, (eng.current_period_id,))
        line_count = cur.fetchone()['count']
        print(f"Total journal lines in period: {line_count}")
        print()
        
        # Check trial balance computation
        print("=" * 80)
        print("TRIAL BALANCE COMPUTATION CHECK")
        print("=" * 80)
        print()
        
        rows = db.compute_trial_balance(
            period_id=eng.current_period_id,
            include_temporary=True,
            conn=eng.conn
        )
        
        print(f"Trial balance rows returned: {len(rows)}")
        print()
        
        if len(rows) == 0:
            print("⚠️  TRIAL BALANCE IS EMPTY!")
            print("This could mean:")
            print("  1. No accounts exist in the database")
            print("  2. All accounts have zero balances")
            print("  3. There's an issue with the compute_trial_balance function")
            print()
        else:
            # Check for accounts with activity
            active_accounts = []
            for r in rows:
                net_debit = float(r.get('net_debit') or 0)
                net_credit = float(r.get('net_credit') or 0)
                if abs(net_debit) > 0.01 or abs(net_credit) > 0.01:
                    active_accounts.append(r)
            
            print(f"Accounts with activity: {len(active_accounts)}")
            print()
            
            if len(active_accounts) == 0:
                print("⚠️  NO ACCOUNTS WITH ACTIVITY!")
                print("All accounts have zero balances.")
                print()
                print("This could mean:")
                print("  1. Journal entries are not posted (status != 'posted')")
                print("  2. Journal entries have no journal lines")
                print("  3. Journal lines have zero amounts")
                print()
            else:
                print("Sample accounts with activity:")
                for acc in active_accounts[:5]:
                    code = acc.get('code', '')
                    name = acc.get('name', '')
                    net_debit = float(acc.get('net_debit') or 0)
                    net_credit = float(acc.get('net_credit') or 0)
                    print(f"  {code} - {name}: Dr {net_debit:,.2f}, Cr {net_credit:,.2f}")
                print()
        
        # Check if entries are posted
        print("=" * 80)
        print("ENTRY STATUS CHECK")
        print("=" * 80)
        print()
        
        cur = eng.conn.execute("""
            SELECT COUNT(*) as count
            FROM journal_entries 
            WHERE period_id = ? AND (status = 'posted' OR status IS NULL)
        """, (eng.current_period_id,))
        posted_count = cur.fetchone()['count']
        
        cur = eng.conn.execute("""
            SELECT COUNT(*) as count
            FROM journal_entries 
            WHERE period_id = ? AND status = 'draft'
        """, (eng.current_period_id,))
        draft_count = cur.fetchone()['count']
        
        print(f"Posted entries (or NULL status): {posted_count}")
        print(f"Draft entries: {draft_count}")
        print()
        
        if draft_count > 0:
            print("⚠️  WARNING: Some entries are in 'draft' status!")
            print("Draft entries are typically not included in trial balance.")
            print("SOLUTION: Post the draft entries.")
            print()
        
        # Summary
        print("=" * 80)
        print("SUMMARY & RECOMMENDATIONS")
        print("=" * 80)
        print()
        
        issues = []
        if len(entries) == 0:
            issues.append("No journal entries in current period")
        if len(rows) == 0:
            issues.append("Trial balance is empty")
        if len(active_accounts) == 0 and len(rows) > 0:
            issues.append("No accounts with activity")
        if draft_count > 0:
            issues.append(f"{draft_count} entries in draft status")
        
        if not issues:
            print("✓ No issues found! Ledger and trial balance should display correctly.")
        else:
            print("⚠️  ISSUES FOUND:")
            for i, issue in enumerate(issues, 1):
                print(f"   {i}. {issue}")
            print()
            print("RECOMMENDED FIXES:")
            if "No journal entries" in str(issues):
                print("1. Make sure you're in the correct accounting period")
                print("2. Create journal entries in the Journal tab")
            if "draft status" in str(issues):
                print("1. Post draft entries by going to Journal tab")
                print("2. Select draft entries and click 'Post'")
            if "No accounts with activity" in str(issues):
                print("1. Check that journal entries have journal lines")
                print("2. Verify journal lines have non-zero amounts")
                print("3. Make sure entries are posted (not draft)")
        
    finally:
        eng.close()

if __name__ == '__main__':
    check_ledger_trial_balance()

