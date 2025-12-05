"""
Check the database that the GUI would use when run from main.py
This simulates what happens when the GUI starts
"""
import sys
import os
from pathlib import Path

# Simulate running from the main.py location
# main.py is in TECHFIX/TECHFIX/, so we need to check what database it would use
main_py_path = Path(__file__).parent / "main.py"
print("=" * 80)
print("CHECKING GUI DATABASE PATH")
print("=" * 80)
print()
print(f"main.py location: {main_py_path}")
print(f"main.py exists: {main_py_path.exists()}")
print()

# The database path is determined by current working directory when db module is imported
# If GUI runs from TECHFIX/TECHFIX/, it would use: TECHFIX/TECHFIX/techfix.sqlite3
# But if it runs from FOR VIDEO/, it would use: FOR VIDEO/techfix.sqlite3

# Check both possible locations
possible_dbs = [
    Path(r"C:\Users\neric\Desktop\FOR VIDEO\techfix.sqlite3"),
    Path(r"C:\Users\neric\Desktop\FOR VIDEO\TECHFIX\TECHFIX\techfix.sqlite3"),
]

print("Checking possible database locations:")
for db_path in possible_dbs:
    exists = db_path.exists()
    size = db_path.stat().st_size if exists else 0
    print(f"  {db_path}")
    print(f"    Exists: {exists}")
    if exists:
        print(f"    Size: {size:,} bytes")
        print(f"    Modified: {db_path.stat().st_mtime}")
    print()

# Now check the one in FOR VIDEO directory (where GUI might run from)
root_db = Path(r"C:\Users\neric\Desktop\FOR VIDEO\techfix.sqlite3")
if root_db.exists():
    print("=" * 80)
    print(f"CHECKING ROOT DATABASE: {root_db}")
    print("=" * 80)
    print()
    
    import sqlite3
    conn = sqlite3.connect(str(root_db))
    conn.row_factory = sqlite3.Row
    
    try:
        # Check periods
        periods = conn.execute("SELECT id, name, start_date, end_date, is_current FROM accounting_periods").fetchall()
        print(f"Accounting Periods: {len(periods)}")
        for p in periods:
            current = " (CURRENT)" if p['is_current'] else ""
            print(f"  Period {p['id']}: {p['name']} ({p['start_date']} to {p['end_date']}){current}")
        print()
        
        # Check entries
        entries = conn.execute("""
            SELECT COUNT(*) as cnt, 
                   MIN(date) as min_date, 
                   MAX(date) as max_date,
                   SUM(CASE WHEN status = 'posted' THEN 1 ELSE 0 END) as posted,
                   SUM(CASE WHEN status = 'draft' THEN 1 ELSE 0 END) as draft
            FROM journal_entries
        """).fetchone()
        
        print(f"Journal Entries:")
        print(f"  Total: {entries['cnt']}")
        print(f"  Posted: {entries['posted']}")
        print(f"  Draft: {entries['draft']}")
        if entries['min_date']:
            print(f"  Date range: {entries['min_date']} to {entries['max_date']}")
        print()
        
        # Get current period
        current_period = conn.execute("SELECT id, name FROM accounting_periods WHERE is_current = 1").fetchone()
        if current_period:
            period_id = current_period['id']
            print(f"Current Period: {current_period['name']} (ID: {period_id})")
            
            # Get max date
            max_date = conn.execute("""
                SELECT MAX(date) as max_date FROM journal_entries 
                WHERE period_id = ? AND status = 'posted'
            """, (period_id,)).fetchone()
            as_of_date = max_date['max_date'] if max_date and max_date['max_date'] else '2025-12-31'
            
            print(f"Balance Sheet as of: {as_of_date}")
            print()
            
            # Calculate balance sheet manually
            from techfix import db as techfix_db
            from techfix.accounting import AccountingEngine
            
            # Create engine with this connection
            eng = AccountingEngine(conn=conn)
            
            balance_sheet = eng.generate_balance_sheet(as_of_date)
            
            assets = balance_sheet.get('assets', [])
            liabilities = balance_sheet.get('liabilities', [])
            equity = balance_sheet.get('equity', [])
            
            total_assets = sum(a.get('amount', 0) for a in assets)
            total_liabilities = sum(l.get('amount', 0) for l in liabilities)
            total_equity = sum(e.get('amount', 0) for e in equity)
            
            print("ASSETS:")
            for asset in assets:
                if abs(asset.get('amount', 0)) > 0.005:
                    print(f"  {asset.get('name'):<40} ₱ {asset.get('amount', 0):>12,.2f}")
            print(f"  {'Total Assets':<40} ₱ {total_assets:>12,.2f}")
            print()
            
            print("LIABILITIES:")
            for liab in liabilities:
                if abs(liab.get('amount', 0)) > 0.005:
                    print(f"  {liab.get('name'):<40} ₱ {liab.get('amount', 0):>12,.2f}")
            if not liabilities or total_liabilities == 0:
                print("  (none)")
            print(f"  {'Total Liabilities':<40} ₱ {total_liabilities:>12,.2f}")
            print()
            
            print("EQUITY:")
            for eq in equity:
                if abs(eq.get('amount', 0)) > 0.005:
                    print(f"  {eq.get('name'):<40} ₱ {eq.get('amount', 0):>12,.2f}")
            print(f"  {'Total Equity':<40} ₱ {total_equity:>12,.2f}")
            print()
            
            balance_check = total_assets - (total_liabilities + total_equity)
            print(f"Balance Check: ₱ {abs(balance_check):,.2f} {'✅' if abs(balance_check) < 0.05 else '❌'}")
            print()
            print("=" * 80)
            print()
            print("THIS IS THE DATABASE THE GUI IS USING!")
            print(f"If these values match what you see in the GUI, this is the correct database.")
            print(f"If they don't match, there might be another database file being used.")
    finally:
        conn.close()
else:
    print(f"Root database not found: {root_db}")
    print("The GUI might be using the database in TECHFIX/TECHFIX/ directory")

