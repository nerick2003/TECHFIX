"""
Analyze why balance sheet as of 2025-12-06 is imbalanced
"""
import sys
import os
from pathlib import Path
import sqlite3

root_db = Path(r"C:\Users\neric\Desktop\FOR VIDEO\techfix.sqlite3")

if not root_db.exists():
    print(f"Database not found: {root_db}")
    sys.exit(1)

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from techfix.accounting import AccountingEngine

conn = sqlite3.connect(str(root_db))
conn.row_factory = sqlite3.Row

try:
    eng = AccountingEngine(conn=conn)
    period_id = eng.current_period_id
    
    print("=" * 80)
    print("ANALYZING BALANCE SHEET DATE MISMATCH")
    print("=" * 80)
    print()
    
    as_of_date = "2025-12-06"
    
    # Get entries up to 2025-12-06
    entries_before = conn.execute("""
        SELECT je.id, je.date, je.description, je.is_closing,
               SUM(CASE WHEN a.type = 'Asset' OR a.type = 'Contra-Asset' THEN jl.debit - jl.credit ELSE 0 END) as asset_change,
               SUM(CASE WHEN a.name = "Owner's Capital" THEN jl.credit - jl.debit ELSE 0 END) as capital_change
        FROM journal_entries je
        JOIN journal_lines jl ON jl.entry_id = je.id
        JOIN accounts a ON a.id = jl.account_id
        WHERE je.period_id = ?
          AND date(je.date) <= date(?)
          AND (je.status = 'posted' OR je.status IS NULL)
        GROUP BY je.id
        ORDER BY je.date, je.id
    """, (period_id, as_of_date)).fetchall()
    
    # Get entries after 2025-12-06
    entries_after = conn.execute("""
        SELECT je.id, je.date, je.description,
               SUM(CASE WHEN a.type = 'Asset' OR a.type = 'Contra-Asset' THEN jl.debit - jl.credit ELSE 0 END) as asset_change,
               SUM(CASE WHEN a.name = "Owner's Capital" THEN jl.credit - jl.debit ELSE 0 END) as capital_change
        FROM journal_entries je
        JOIN journal_lines jl ON jl.entry_id = je.id
        JOIN accounts a ON a.id = jl.account_id
        WHERE je.period_id = ?
          AND date(je.date) > date(?)
          AND (je.status = 'posted' OR je.status IS NULL)
        GROUP BY je.id
        ORDER BY je.date, je.id
    """, (period_id, as_of_date)).fetchall()
    
    print(f"Entries up to {as_of_date}: {len(entries_before)}")
    print()
    for entry in entries_before:
        closing = " [CLOSING]" if entry['is_closing'] else ""
        asset_chg = float(entry['asset_change'] or 0)
        cap_chg = float(entry['capital_change'] or 0)
        print(f"Entry #{entry['id']}: {entry['date']} - {entry['description']}{closing}")
        if abs(asset_chg) > 0.01:
            print(f"  Asset change: ₱ {asset_chg:,.2f}")
        if abs(cap_chg) > 0.01:
            print(f"  Capital change: ₱ {cap_chg:,.2f}")
    print()
    
    total_assets_before = sum(float(e['asset_change'] or 0) for e in entries_before)
    total_capital_before = sum(float(e['capital_change'] or 0) for e in entries_before)
    
    print(f"Total Assets up to {as_of_date}: ₱ {total_assets_before:,.2f}")
    print(f"Total Capital up to {as_of_date}: ₱ {total_capital_before:,.2f}")
    print()
    
    if entries_after:
        print(f"Entries AFTER {as_of_date}: {len(entries_after)}")
        print()
        for entry in entries_after:
            asset_chg = float(entry['asset_change'] or 0)
            cap_chg = float(entry['capital_change'] or 0)
            print(f"Entry #{entry['id']}: {entry['date']} - {entry['description']}")
            if abs(asset_chg) > 0.01:
                print(f"  Asset change: ₱ {asset_chg:,.2f}")
            if abs(cap_chg) > 0.01:
                print(f"  Capital change: ₱ {cap_chg:,.2f}")
        print()
        
        total_assets_after = sum(float(e['asset_change'] or 0) for e in entries_after)
        total_capital_after = sum(float(e['capital_change'] or 0) for e in entries_after)
        
        print(f"Total Assets from entries AFTER {as_of_date}: ₱ {total_assets_after:,.2f}")
        print(f"Total Capital from entries AFTER {as_of_date}: ₱ {total_capital_after:,.2f}")
        print()
        
        print("=" * 80)
        print("THE PROBLEM")
        print("=" * 80)
        print()
        print(f"When viewing balance sheet 'As of {as_of_date}':")
        print(f"  Assets include only entries up to {as_of_date}: ₱ {total_assets_before:,.2f}")
        print(f"  But Owner's Capital includes net income from closing entries")
        print(f"  which closed ALL revenue/expenses (including future ones): ₱ {total_capital_before:,.2f}")
        print()
        print(f"The difference (₱ {abs(total_assets_before - total_capital_before):,.2f}) represents")
        print(f"assets from transactions that happened AFTER {as_of_date}.")
        print()
        print("SOLUTION:")
        print(f"  - View balance sheet 'As of 2025-12-31' (or latest date) to see balanced sheet")
        print(f"  - OR: The closing entries should only close revenue/expenses up to the closing date")
        print(f"    (not the entire period)")
    
finally:
    conn.close()

