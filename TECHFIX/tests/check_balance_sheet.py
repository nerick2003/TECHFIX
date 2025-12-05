#!/usr/bin/env python3
"""
Diagnostic script to check why the balance sheet doesn't balance.
This script analyzes the database and reports all issues found.
"""

import sqlite3
import sys
from pathlib import Path
from datetime import date

# Add the techfix module to path
sys.path.insert(0, str(Path(__file__).parent))

from techfix import db, accounting

def format_currency(amount):
    """Format amount as currency."""
    return f"₱{amount:,.2f}"

def check_database():
    """Check the database for balance sheet issues."""
    print("=" * 80)
    print("BALANCE SHEET DIAGNOSTIC REPORT")
    print("=" * 80)
    print()
    
    # Connect to database
    conn = db.get_connection()
    
    try:
        # Get current period
        current_period = conn.execute("""
            SELECT id, name, start_date, end_date 
            FROM accounting_periods 
            WHERE is_current = 1
        """).fetchone()
        
        if not current_period:
            print("⚠ No current accounting period found!")
            print("   Please create or set a current accounting period.")
            return
        
        period_id = current_period['id']
        period_name = current_period['name']
        print(f"Current Period: {period_name} (ID: {period_id})")
        if current_period['start_date']:
            print(f"  Start Date: {current_period['start_date']}")
        if current_period['end_date']:
            print(f"  End Date: {current_period['end_date']}")
        print()
        
        # Check 1: Draft transactions
        print("=" * 80)
        print("CHECK 1: DRAFT TRANSACTIONS")
        print("=" * 80)
        drafts = conn.execute("""
            SELECT id, date, description, document_ref, status
            FROM journal_entries 
            WHERE period_id = ? AND status = 'draft'
            ORDER BY date, id
        """, (period_id,)).fetchall()
        
        if drafts:
            print(f"⚠ Found {len(drafts)} draft transaction(s) that are NOT included in balance sheet:")
            print()
            for d in drafts:
                print(f"  Entry #{d['id']}: {d['date']} - {d['description']}")
                if d['document_ref']:
                    print(f"    Reference: {d['document_ref']}")
            print()
            print("  ACTION REQUIRED: Post these transactions using 'Record & Post' button.")
        else:
            print("✓ No draft transactions found.")
        print()
        
        # Check 2: Unbalanced entries
        print("=" * 80)
        print("CHECK 2: UNBALANCED JOURNAL ENTRIES")
        print("=" * 80)
        unbalanced = conn.execute("""
            SELECT je.id, je.date, je.description, 
                   SUM(jl.debit) as total_debit, SUM(jl.credit) as total_credit,
                   ABS(SUM(jl.debit) - SUM(jl.credit)) as difference
            FROM journal_entries je
            JOIN journal_lines jl ON jl.entry_id = je.id
            WHERE je.period_id = ? AND je.status = 'posted'
            GROUP BY je.id
            HAVING ABS(SUM(jl.debit) - SUM(jl.credit)) > 0.01
            ORDER BY je.date, je.id
        """, (period_id,)).fetchall()
        
        if unbalanced:
            print(f"⚠ Found {len(unbalanced)} unbalanced journal entry/entries:")
            print()
            for u in unbalanced:
                print(f"  Entry #{u['id']}: {u['date']} - {u['description']}")
                print(f"    Debit Total: {format_currency(u['total_debit'])}")
                print(f"    Credit Total: {format_currency(u['total_credit'])}")
                print(f"    Difference: {format_currency(u['difference'])}")
                print()
            print("  ACTION REQUIRED: Each entry must have equal debits and credits.")
        else:
            print("✓ All posted entries are balanced (debits = credits).")
        print()
        
        # Check 3: Entries with only one line
        print("=" * 80)
        print("CHECK 3: ENTRIES WITH ONLY ONE LINE")
        print("=" * 80)
        single_line = conn.execute("""
            SELECT je.id, je.date, je.description, COUNT(jl.id) as line_count
            FROM journal_entries je
            JOIN journal_lines jl ON jl.entry_id = je.id
            WHERE je.period_id = ? AND je.status = 'posted'
            GROUP BY je.id
            HAVING COUNT(jl.id) < 2
            ORDER BY je.date, je.id
        """, (period_id,)).fetchall()
        
        if single_line:
            print(f"⚠ Found {len(single_line)} entry/entries with only one line:")
            print()
            for s in single_line:
                print(f"  Entry #{s['id']}: {s['date']} - {s['description']}")
                print(f"    Lines: {s['line_count']}")
            print()
            print("  ACTION REQUIRED: Each transaction needs both a debit and credit line.")
        else:
            print("✓ All entries have at least 2 lines (debit and credit).")
        print()
        
        # Check 4: Entries with zero amounts
        print("=" * 80)
        print("CHECK 4: ENTRIES WITH ZERO AMOUNTS")
        print("=" * 80)
        zero_amount = conn.execute("""
            SELECT DISTINCT je.id, je.date, je.description
            FROM journal_entries je
            JOIN journal_lines jl ON jl.entry_id = je.id
            WHERE je.period_id = ? AND je.status = 'posted'
              AND jl.debit = 0 AND jl.credit = 0
            ORDER BY je.date, je.id
        """, (period_id,)).fetchall()
        
        if zero_amount:
            print(f"⚠ Found {len(zero_amount)} entry/entries with zero amounts:")
            print()
            for z in zero_amount:
                print(f"  Entry #{z['id']}: {z['date']} - {z['description']}")
            print()
            print("  NOTE: These won't affect the balance sheet but should be reviewed.")
        else:
            print("✓ No entries with zero amounts found.")
        print()
        
        # Check 5: Transactions not in current period
        print("=" * 80)
        print("CHECK 5: TRANSACTIONS NOT IN CURRENT PERIOD")
        print("=" * 80)
        wrong_period = conn.execute("""
            SELECT COUNT(*) as cnt FROM journal_entries 
            WHERE (period_id IS NULL OR period_id != ?) AND status = 'posted'
        """, (period_id,)).fetchone()
        
        if wrong_period and wrong_period['cnt'] > 0:
            print(f"⚠ Found {wrong_period['cnt']} posted transaction(s) not in current period.")
            print("  NOTE: These won't appear in the current period's balance sheet.")
        else:
            print("✓ All posted transactions are in the current period.")
        print()
        
        # Check 6: Calculate actual balance sheet
        print("=" * 80)
        print("CHECK 6: BALANCE SHEET CALCULATION")
        print("=" * 80)
        
        # Get the most recent date for balance sheet
        max_date = conn.execute("""
            SELECT MAX(date) as max_date FROM journal_entries 
            WHERE period_id = ? AND status = 'posted'
        """, (period_id,)).fetchone()
        
        as_of_date = max_date['max_date'] if max_date and max_date['max_date'] else date.today().isoformat()
        print(f"Balance Sheet as of: {as_of_date}")
        print()
        
        # Also check at today's date
        today_date = date.today().isoformat()
        if today_date != as_of_date:
            print(f"Also checking balance sheet as of today ({today_date}):")
            print()
            engine_today = accounting.AccountingEngine(conn=conn)
            engine_today.set_active_period(period_id)
            balance_sheet_today = engine_today.generate_balance_sheet(today_date)
            balance_check_today = balance_sheet_today.get('balance_check', 0.0)
            if abs(balance_check_today) > 0.01:
                print(f"⚠ Balance sheet as of {today_date} has difference: {format_currency(abs(balance_check_today))}")
            else:
                print(f"✓ Balance sheet as of {today_date} is balanced.")
            print()
            print("(Continuing with most recent transaction date below...)")
            print()
        
        # Generate balance sheet using the engine
        engine = accounting.AccountingEngine(conn=conn)
        engine.set_active_period(period_id)
        balance_sheet = engine.generate_balance_sheet(as_of_date)
        
        total_assets = balance_sheet.get('total_assets', 0.0)
        total_liabilities = balance_sheet.get('total_liabilities', 0.0)
        total_equity = balance_sheet.get('total_equity', 0.0)
        balance_check = balance_sheet.get('balance_check', 0.0)
        
        print("ASSETS:")
        for asset in balance_sheet.get('assets', []):
            amount = asset.get('amount', 0.0)
            if abs(amount) > 0.005:
                print(f"  {asset.get('name', 'Unknown')}: {format_currency(amount)}")
        print(f"  Total Assets: {format_currency(total_assets)}")
        print()
        
        print("LIABILITIES:")
        for liab in balance_sheet.get('liabilities', []):
            amount = liab.get('amount', 0.0)
            if abs(amount) > 0.005:
                print(f"  {liab.get('name', 'Unknown')}: {format_currency(amount)}")
        print(f"  Total Liabilities: {format_currency(total_liabilities)}")
        print()
        
        print("EQUITY:")
        for eq in balance_sheet.get('equity', []):
            amount = eq.get('amount', 0.0)
            if abs(amount) > 0.005:
                print(f"  {eq.get('name', 'Unknown')}: {format_currency(amount)}")
        print(f"  Total Equity: {format_currency(total_equity)}")
        print()
        
        total_liab_equity = total_liabilities + total_equity
        print("=" * 80)
        print("BALANCE CHECK:")
        print("=" * 80)
        print(f"Total Assets: {format_currency(total_assets)}")
        print(f"Total Liabilities + Equity: {format_currency(total_liab_equity)}")
        print(f"Difference: {format_currency(abs(balance_check))}")
        
        if abs(balance_check) > 0.01:
            print()
            print("⚠ BALANCE SHEET DOES NOT BALANCE!")
            print()
            print("Possible causes:")
            if drafts:
                print(f"  • {len(drafts)} draft transaction(s) need to be posted")
            if unbalanced:
                print(f"  • {len(unbalanced)} unbalanced entry/entries need to be fixed")
            if single_line:
                print(f"  • {len(single_line)} entry/entries missing debit or credit line")
            if not drafts and not unbalanced and not single_line:
                print("  • Check for missing transactions or data entry errors")
                print("  • Verify all accounts are correctly classified")
                print("  • Ensure closing entries have been made if period should be closed")
        else:
            print()
            print("✓ BALANCE SHEET IS BALANCED!")
        
        print()
        print("=" * 80)
        print("END OF REPORT")
        print("=" * 80)
        
    finally:
        conn.close()

if __name__ == "__main__":
    try:
        check_database()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

