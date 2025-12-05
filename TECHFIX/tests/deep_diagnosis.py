#!/usr/bin/env python3
"""
Deep diagnosis of the balance sheet imbalance issue.
This will check every transaction and account balance.
"""

import sqlite3
import sys
from pathlib import Path

# Check the database in the root directory (GUI database)
root_db = Path(r"C:\Users\neric\Desktop\FOR VIDEO\techfix.sqlite3")

if not root_db.exists():
    print(f"Database not found: {root_db}")
    sys.exit(1)

conn = sqlite3.connect(str(root_db))
conn.row_factory = sqlite3.Row

try:
    # Get current period
    period = conn.execute("SELECT id, name FROM accounting_periods WHERE is_current = 1").fetchone()
    if not period:
        print("No current period found!")
        sys.exit(1)
    
    period_id = period['id']
    period_name = period['name']
    print("=" * 80)
    print("DEEP DIAGNOSIS - BALANCE SHEET IMBALANCE")
    print("=" * 80)
    print(f"Period: {period_name} (ID: {period_id})")
    print()
    
    # Get max date
    max_date = conn.execute("""
        SELECT MAX(date) as max_date FROM journal_entries 
        WHERE period_id = ? AND status = 'posted'
    """, (period_id,)).fetchone()
    as_of_date = max_date['max_date'] if max_date and max_date['max_date'] else '2025-12-31'
    print(f"As of date: {as_of_date}")
    print()
    
    # Get all journal entries
    print("=" * 80)
    print("ALL JOURNAL ENTRIES (Posted Only)")
    print("=" * 80)
    entries = conn.execute("""
        SELECT je.id, je.date, je.description, je.status, je.is_adjusting, je.is_closing
        FROM journal_entries je
        WHERE je.period_id = ? AND je.status = 'posted'
        ORDER BY je.date, je.id
    """, (period_id,)).fetchall()
    
    print(f"Total entries: {len(entries)}")
    print()
    
    # Check each entry for balance
    unbalanced_entries = []
    for entry in entries:
        lines = conn.execute("""
            SELECT jl.account_id, jl.debit, jl.credit, a.name as account_name, a.type as account_type
            FROM journal_lines jl
            JOIN accounts a ON a.id = jl.account_id
            WHERE jl.entry_id = ?
        """, (entry['id'],)).fetchall()
        
        total_debit = sum(float(l['debit']) for l in lines)
        total_credit = sum(float(l['credit']) for l in lines)
        difference = abs(total_debit - total_credit)
        
        if difference > 0.01:
            unbalanced_entries.append({
                'entry': entry,
                'lines': lines,
                'debit': total_debit,
                'credit': total_credit,
                'difference': difference
            })
    
    if unbalanced_entries:
        print(f"⚠ Found {len(unbalanced_entries)} unbalanced entries:")
        for ue in unbalanced_entries:
            e = ue['entry']
            print(f"\nEntry #{e['id']}: {e['date']} - {e['description']}")
            print(f"  Debit Total: {ue['debit']:.2f}")
            print(f"  Credit Total: {ue['credit']:.2f}")
            print(f"  Difference: {ue['difference']:.2f}")
            print("  Lines:")
            for line in ue['lines']:
                print(f"    {line['account_name']} ({line['account_type']}): "
                      f"Debit={line['debit']:.2f}, Credit={line['credit']:.2f}")
    else:
        print("✓ All entries are balanced (debits = credits)")
    print()
    
    # Calculate account balances manually
    print("=" * 80)
    print("ACCOUNT BALANCES (Permanent Accounts Only)")
    print("=" * 80)
    
    account_balances = conn.execute("""
        SELECT 
            a.id,
            a.code,
            a.name,
            a.type,
            a.normal_side,
            COALESCE(SUM(jl.debit), 0) as total_debit,
            COALESCE(SUM(jl.credit), 0) as total_credit,
            (COALESCE(SUM(jl.debit), 0) - COALESCE(SUM(jl.credit), 0)) as balance
        FROM accounts a
        LEFT JOIN journal_lines jl ON jl.account_id = a.id
        LEFT JOIN journal_entries je ON je.id = jl.entry_id
        WHERE a.is_active = 1 
          AND a.is_permanent = 1
          AND (je.status = 'posted' OR je.status IS NULL OR je.id IS NULL)
          AND (je.period_id = ? OR je.period_id IS NULL)
          AND (date(je.date) <= date(?) OR je.date IS NULL)
        GROUP BY a.id, a.code, a.name, a.type, a.normal_side
        HAVING ABS(COALESCE(SUM(jl.debit), 0) - COALESCE(SUM(jl.credit), 0)) > 0.005
        ORDER BY a.type, a.code
    """, (period_id, as_of_date)).fetchall()
    
    assets = []
    liabilities = []
    equity = []
    total_assets_calc = 0.0
    total_liabilities_calc = 0.0
    total_equity_calc = 0.0
    
    print("ASSETS:")
    for acc in account_balances:
        acc_type = (acc['type'] or '').lower()
        balance = float(acc['balance'])
        
        if acc_type == 'asset':
            amount = round(balance, 2)
            if abs(amount) > 0.005:
                print(f"  {acc['name']}: {balance:,.2f}")
                assets.append({'name': acc['name'], 'amount': amount})
                total_assets_calc += amount
        elif acc_type == 'contra asset':
            # Contra assets reduce asset value
            credit_balance = -balance  # balance is already debit - credit, so negative means credit
            amount = round(credit_balance, 2)
            if abs(amount) > 0.005:
                print(f"  {acc['name']}: {-amount:,.2f} (contra)")
                assets.append({'name': acc['name'], 'amount': -amount})
                total_assets_calc -= amount
    
    print(f"  Total Assets: {total_assets_calc:,.2f}")
    print()
    
    print("LIABILITIES:")
    for acc in account_balances:
        acc_type = (acc['type'] or '').lower()
        balance = float(acc['balance'])
        
        if acc_type == 'liability':
            # Liabilities have credit balances (negative in our calculation)
            amount = round(-balance, 2)  # Negate because balance is debit - credit
            if amount < 0:
                # Overpayment - treat as prepaid asset
                prepaid = abs(amount)
                print(f"  Prepaid ({acc['name']}): {prepaid:,.2f}")
                assets.append({'name': f"Prepaid ({acc['name']})", 'amount': prepaid})
                total_assets_calc += prepaid
            elif abs(amount) > 0.005:
                print(f"  {acc['name']}: {amount:,.2f}")
                liabilities.append({'name': acc['name'], 'amount': amount})
                total_liabilities_calc += amount
    
    print(f"  Total Liabilities: {total_liabilities_calc:,.2f}")
    print()
    
    print("EQUITY:")
    for acc in account_balances:
        acc_type = (acc['type'] or '').lower()
        balance = float(acc['balance'])
        account_name = acc['name']
        
        if acc_type == 'equity':
            if 'drawing' in account_name.lower() or 'withdrawal' in account_name.lower():
                # Drawings reduce equity
                drawings_amount = round(balance, 2)  # balance is already debit - credit
                if abs(drawings_amount) > 0.005:
                    print(f"  {account_name}: {-abs(drawings_amount):,.2f}")
                    equity.append({'name': account_name, 'amount': -abs(drawings_amount)})
                    total_equity_calc -= abs(drawings_amount)
            else:
                # Equity has credit balances
                amount = round(-balance, 2)  # Negate because balance is debit - credit
                if abs(amount) > 0.005:
                    print(f"  {account_name}: {amount:,.2f}")
                    equity.append({'name': account_name, 'amount': amount})
                    total_equity_calc += amount
    
    print(f"  Total Equity: {total_equity_calc:,.2f}")
    print()
    
    print("=" * 80)
    print("BALANCE CHECK")
    print("=" * 80)
    print(f"Total Assets: {total_assets_calc:,.2f}")
    print(f"Total Liabilities: {total_liabilities_calc:,.2f}")
    print(f"Total Equity: {total_equity_calc:,.2f}")
    total_liab_equity = total_liabilities_calc + total_equity_calc
    print(f"Total Liabilities + Equity: {total_liab_equity:,.2f}")
    difference = total_assets_calc - total_liab_equity
    print(f"Difference: {abs(difference):,.2f}")
    print()
    
    if abs(difference) > 0.01:
        print("⚠ BALANCE SHEET DOES NOT BALANCE!")
        print()
        print("Possible causes:")
        print("1. Missing transactions")
        print("2. Transactions not posted")
        print("3. Calculation error in the code")
        print("4. Accounts misclassified")
    else:
        print("✓ BALANCE SHEET IS BALANCED!")
        print()
        print("If GUI shows different values, there may be a display/calculation bug.")
    
    # Check for missing accounts or transactions
    print()
    print("=" * 80)
    print("CHECKING FOR MISSING DATA")
    print("=" * 80)
    
    # Check for entries without lines
    entries_no_lines = conn.execute("""
        SELECT je.id, je.date, je.description
        FROM journal_entries je
        LEFT JOIN journal_lines jl ON jl.entry_id = je.id
        WHERE je.period_id = ? AND je.status = 'posted' AND jl.id IS NULL
    """, (period_id,)).fetchall()
    
    if entries_no_lines:
        print(f"⚠ Found {len(entries_no_lines)} entries without journal lines:")
        for e in entries_no_lines:
            print(f"  Entry #{e['id']}: {e['date']} - {e['description']}")
    else:
        print("✓ All entries have journal lines")
    
    print()
    
    # Check for draft entries
    drafts = conn.execute("""
        SELECT COUNT(*) as cnt FROM journal_entries 
        WHERE period_id = ? AND status = 'draft'
    """, (period_id,)).fetchone()
    
    if drafts and drafts['cnt'] > 0:
        print(f"⚠ Found {drafts['cnt']} draft entries (not included in balance sheet)")
    else:
        print("✓ No draft entries")
    
finally:
    conn.close()

