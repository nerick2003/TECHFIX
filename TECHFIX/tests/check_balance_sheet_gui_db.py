#!/usr/bin/env python3
"""
Check the database file that the GUI is likely using.
This checks the database in the root directory (where GUI might be launched from).
"""

import sqlite3
import sys
from pathlib import Path
from datetime import date

# Check the database in the root directory
root_db = Path(r"C:\Users\neric\Desktop\FOR VIDEO\techfix.sqlite3")

if not root_db.exists():
    print(f"Database not found: {root_db}")
    sys.exit(1)

print("=" * 80)
print("CHECKING GUI DATABASE")
print("=" * 80)
print(f"Database: {root_db}")
print()

conn = sqlite3.connect(str(root_db))
conn.row_factory = sqlite3.Row

try:
    # Get current period
    current_period = conn.execute("""
        SELECT id, name, start_date, end_date 
        FROM accounting_periods 
        WHERE is_current = 1
    """).fetchone()
    
    if not current_period:
        print("⚠ No current accounting period found!")
        sys.exit(1)
    
    period_id = current_period['id']
    period_name = current_period['name']
    print(f"Current Period: {period_name} (ID: {period_id})")
    print()
    
    # Check for draft transactions
    drafts = conn.execute("""
        SELECT COUNT(*) as cnt FROM journal_entries 
        WHERE period_id = ? AND status = 'draft'
    """, (period_id,)).fetchone()
    
    if drafts and drafts['cnt'] > 0:
        print(f"⚠ Found {drafts['cnt']} draft transaction(s)")
        draft_list = conn.execute("""
            SELECT id, date, description FROM journal_entries 
            WHERE period_id = ? AND status = 'draft'
            ORDER BY date, id
        """, (period_id,)).fetchall()
        for d in draft_list:
            print(f"  Entry #{d['id']}: {d['date']} - {d['description']}")
    else:
        print("✓ No draft transactions")
    print()
    
    # Check unbalanced entries
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
        print(f"⚠ Found {len(unbalanced)} unbalanced entry/entries:")
        for u in unbalanced:
            print(f"  Entry #{u['id']}: {u['date']} - {u['description']}")
            print(f"    Debit: {u['total_debit']:.2f}, Credit: {u['total_credit']:.2f}, Diff: {u['difference']:.2f}")
    else:
        print("✓ All entries are balanced")
    print()
    
    # Calculate balance sheet manually
    print("=" * 80)
    print("BALANCE SHEET CALCULATION")
    print("=" * 80)
    
    # Get max date
    max_date = conn.execute("""
        SELECT MAX(date) as max_date FROM journal_entries 
        WHERE period_id = ? AND status = 'posted'
    """, (period_id,)).fetchone()
    
    as_of_date = max_date['max_date'] if max_date and max_date['max_date'] else date.today().isoformat()
    print(f"As of: {as_of_date}")
    print()
    
    # Get trial balance for permanent accounts only
    rows = conn.execute("""
        SELECT a.id, a.code, a.name, a.type, a.normal_side,
               ROUND(CASE WHEN (COALESCE(SUM(jl.debit),0) - COALESCE(SUM(jl.credit),0)) > 0 
                    THEN (COALESCE(SUM(jl.debit),0) - COALESCE(SUM(jl.credit),0)) ELSE 0 END, 2) AS net_debit,
               ROUND(CASE WHEN (COALESCE(SUM(jl.debit),0) - COALESCE(SUM(jl.credit),0)) < 0 
                    THEN -(COALESCE(SUM(jl.debit),0) - COALESCE(SUM(jl.credit),0)) ELSE 0 END, 2) AS net_credit
        FROM accounts a
        LEFT JOIN journal_lines jl ON jl.account_id = a.id
        LEFT JOIN journal_entries je ON je.id = jl.entry_id
        WHERE a.is_active = 1 
          AND a.is_permanent = 1
          AND (je.status = 'posted' OR je.status IS NULL OR je.id IS NULL)
          AND (je.period_id = ? OR je.period_id IS NULL)
          AND (date(je.date) <= date(?) OR je.date IS NULL)
        GROUP BY a.id, a.code, a.name, a.type, a.normal_side
        ORDER BY a.code
    """, (period_id, as_of_date)).fetchall()
    
    total_assets = 0.0
    total_liabilities = 0.0
    total_equity = 0.0
    
    print("ASSETS:")
    for r in rows:
        acc_type = (r["type"] or "").lower()
        net_debit = float(r["net_debit"] or 0.0)
        net_credit = float(r["net_credit"] or 0.0)
        
        if acc_type == "asset":
            balance = net_debit - net_credit
            amount = round(balance, 2)
            if abs(amount) > 0.005:
                print(f"  {r['name']}: ₱{amount:,.2f}")
                total_assets += amount
        elif acc_type == "contra asset":
            credit_balance = net_credit - net_debit
            amount = round(credit_balance, 2)
            if abs(amount) > 0.005:
                print(f"  {r['name']}: ₱{-amount:,.2f}")
                total_assets -= amount
    
    print(f"  Total Assets: ₱{total_assets:,.2f}")
    print()
    
    print("LIABILITIES:")
    for r in rows:
        acc_type = (r["type"] or "").lower()
        net_debit = float(r["net_debit"] or 0.0)
        net_credit = float(r["net_credit"] or 0.0)
        
        if acc_type == "liability":
            balance = net_credit - net_debit
            amount = round(balance, 2)
            if amount < 0:
                # Overpayment - treat as prepaid asset
                prepaid = abs(amount)
                print(f"  Prepaid ({r['name']}): ₱{prepaid:,.2f}")
                total_assets += prepaid
            elif abs(amount) > 0.005:
                print(f"  {r['name']}: ₱{amount:,.2f}")
                total_liabilities += amount
    
    print(f"  Total Liabilities: ₱{total_liabilities:,.2f}")
    print()
    
    print("EQUITY:")
    for r in rows:
        acc_type = (r["type"] or "").lower()
        net_debit = float(r["net_debit"] or 0.0)
        net_credit = float(r["net_credit"] or 0.0)
        account_name = r["name"]
        
        if acc_type == "equity":
            if "drawing" in account_name.lower() or "withdrawal" in account_name.lower():
                drawings_amount = round(net_debit - net_credit, 2)
                if abs(drawings_amount) > 0.005:
                    print(f"  {account_name}: ₱{-abs(drawings_amount):,.2f}")
                    total_equity -= drawings_amount
            else:
                balance = net_credit - net_debit
                amount = round(balance, 2)
                if abs(amount) > 0.005:
                    print(f"  {account_name}: ₱{amount:,.2f}")
                    total_equity += amount
    
    print(f"  Total Equity: ₱{total_equity:,.2f}")
    print()
    
    print("=" * 80)
    print("BALANCE CHECK:")
    print("=" * 80)
    print(f"Total Assets: ₱{total_assets:,.2f}")
    print(f"Total Liabilities: ₱{total_liabilities:,.2f}")
    print(f"Total Equity: ₱{total_equity:,.2f}")
    total_liab_equity = total_liabilities + total_equity
    print(f"Total Liabilities + Equity: ₱{total_liab_equity:,.2f}")
    difference = total_assets - total_liab_equity
    print(f"Difference: ₱{abs(difference):,.2f}")
    
    if abs(difference) > 0.01:
        print()
        print("⚠ BALANCE SHEET DOES NOT BALANCE!")
        print()
        print("This matches what you see in the GUI!")
    else:
        print()
        print("✓ BALANCE SHEET IS BALANCED!")
    
finally:
    conn.close()

